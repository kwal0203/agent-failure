from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID, NAMESPACE_URL, uuid4, uuid5

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.models import (
    EvaluatorResultModel,
    SessionModel,
)
from apps.control_plane.src.interfaces.http.auth import Principal, get_current_principal
import apps.control_plane.src.interfaces.http.main as main_module
from apps.control_plane.src.interfaces.http.main import app


def _override_db_session(db_session: Session):
    def _dependency_override():
        try:
            yield db_session
        finally:
            pass

    return _dependency_override


def _override_principal(user_id: UUID, role: str) -> Callable[[], Principal]:
    def _dependency_override() -> Principal:
        return Principal(user_id=user_id, role=role)

    return _dependency_override


def _owner_user_id(username: str) -> UUID:
    return uuid5(namespace=NAMESPACE_URL, name=f"local-user:{username}")


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_get_evaluator_feedback_returns_200_empty_feedback(db_session: Session) -> None:
    session_id = uuid4()
    owner_username = "owner-user"
    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=uuid4(),
            lab_version_id=uuid4(),
            owner_user_id=_owner_user_id(owner_username),
            state="ACTIVE",
            last_transition_actor="seed",
            last_transition_reason=None,
        )
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions/{session_id}/evaluator-feedback",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["feedback"] == []


def test_get_evaluator_feedback_returns_200_populated_feedback(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "owner-user"
    lab_id = uuid4()
    lab_version_id = uuid4()

    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=lab_id,
            lab_version_id=lab_version_id,
            owner_user_id=_owner_user_id(owner_username),
            state="ACTIVE",
            last_transition_actor="seed",
            last_transition_reason=None,
        )
    )
    db_session.flush()
    db_session.add_all(
        [
            EvaluatorResultModel(
                id=uuid4(),
                idempotency_key=f"idempo:{uuid4()}",
                result_type="constraint_violation",
                code="pi.secret_exfiltration_success",
                trigger_event_index=1,
                trigger_start_event_index=None,
                trigger_end_event_index=None,
                feedback_level="flag",
                reason_code="PI_SECRET_EXFILTRATION_DETECTED",
                feedback_payload={"matched_value": "FLAG{abc123}"},
                created_at=datetime.now(timezone.utc),
                session_id=session_id,
                lab_id=lab_id,
                lab_version_id=lab_version_id,
                evaluator_version=1,
            ),
            EvaluatorResultModel(
                id=uuid4(),
                idempotency_key=f"idempo:{uuid4()}",
                result_type="partial_success",
                code="pi.attack_attempt_blocked",
                trigger_event_index=2,
                trigger_start_event_index=None,
                trigger_end_event_index=None,
                feedback_level="hint",
                reason_code="PI_ATTACK_ATTEMPT_BLOCKED",
                feedback_payload={
                    "blocked_by": "model_policy",
                    "block_reason_code": "POLICY_DENIED",
                },
                created_at=datetime.now(timezone.utc),
                session_id=session_id,
                lab_id=lab_id,
                lab_version_id=lab_version_id,
                evaluator_version=1,
            ),
        ]
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions/{session_id}/evaluator-feedback",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert len(body["feedback"]) == 2

    first = body["feedback"][0]
    assert first["status"] == "learned"
    assert first["reason_code"] == "PI_SECRET_EXFILTRATION_DETECTED"
    assert first["evidence_snippet"] == "FLAG{abc123}"

    second = body["feedback"][1]
    assert second["status"] == "progress"
    assert second["reason_code"] == "PI_ATTACK_ATTEMPT_BLOCKED"
    assert (
        second["evidence_snippet"]
        == "Attack attempt blocked by model_policy (POLICY_DENIED)"
    )


def test_get_evaluator_feedback_returns_403_for_forbidden_role(
    db_session: Session,
) -> None:
    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_current_principal] = _override_principal(
        user_id=uuid4(), role="viewer"
    )
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions/{uuid4()}/evaluator-feedback",
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "FORBIDDEN"
    assert body["error"]["retryable"] is False


def test_get_evaluator_feedback_returns_500_on_unexpected_error(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _boom(**kwargs):
        _ = kwargs
        raise RuntimeError("boom")

    monkeypatch.setattr(main_module, "get_session_evaluator_feedback", _boom)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions/{uuid4()}/evaluator-feedback",
            headers=_auth_header(token="local:learner-user:learner"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["retryable"] is False
