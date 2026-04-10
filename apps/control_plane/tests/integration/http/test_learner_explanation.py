from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from typing import cast

from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.models import (
    LearnerExplanationModel,
    OutboxEventModel,
    SessionModel,
    TraceEventModel,
)
from apps.control_plane.src.interfaces.http.main import app


_UNSET = object()


def _override_db_session(db_session: Session):
    def _dependency_override():
        try:
            yield db_session
        finally:
            pass

    return _dependency_override


def _owner_user_id(username: str) -> UUID:
    return uuid5(namespace=NAMESPACE_URL, name=f"local-user:{username}")


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_session(
    db_session: Session,
    *,
    owner_username: str,
    state: SessionState,
    lab_id: UUID | None | object = _UNSET,
    lab_version_id: UUID | None | object = _UNSET,
    lab_difficulty: str = "medium",
) -> SessionModel:
    resolved_lab_id = cast(UUID | None, uuid4() if lab_id is _UNSET else lab_id)
    resolved_lab_version_id = cast(
        UUID | None, uuid4() if lab_version_id is _UNSET else lab_version_id
    )
    session = SessionModel(
        id=uuid4(),
        lab_id=resolved_lab_id,
        lab_version_id=resolved_lab_version_id,
        owner_user_id=_owner_user_id(owner_username),
        state=state.value,
        runtime_substate="WAITING_FOR_INPUT" if state == SessionState.ACTIVE else None,
        resume_mode="hot_resume",
        last_transition_actor="seed",
        last_transition_reason=None,
        lab_difficulty=lab_difficulty,
    )
    db_session.add(session)
    db_session.flush()
    return session


def _request_body(
    explanation: str = "I trusted untrusted email instructions over system policy.",
) -> dict[str, object]:
    return {"explanation": explanation}


@pytest.mark.usefixtures("engine")
def test_learner_explanation_success_returns_202_and_persists_side_effects(
    db_session: Session,
) -> None:
    owner_username = "owner-user"
    session = _seed_session(
        db_session, owner_username=owner_username, state=SessionState.COMPLETED
    )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/sessions/{session.id}/explanation",
            headers={
                **_auth_header(token=f"local:{owner_username}"),
                "Idempotency-Key": "explain-key-1",
            },
            json=_request_body(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    body = response.json()
    assert body["session_id"] == str(session.id)
    assert body["accepted"] is True

    explanation_count = db_session.execute(
        select(func.count()).select_from(LearnerExplanationModel)
    ).scalar_one()
    assert explanation_count == 1

    trace_count = db_session.execute(
        select(func.count())
        .select_from(TraceEventModel)
        .where(
            TraceEventModel.session_id == session.id,
            TraceEventModel.event_type == "LEARNER_EXPLANATION_SUBMITTED",
        )
    ).scalar_one()
    assert trace_count == 1

    evaluate_outbox_count = db_session.execute(
        select(func.count())
        .select_from(OutboxEventModel)
        .where(
            OutboxEventModel.aggregate_id == session.id,
            OutboxEventModel.event_type == "session.evaluate.requested.v1",
        )
    ).scalar_one()
    assert evaluate_outbox_count == 1


@pytest.mark.usefixtures("engine")
def test_learner_explanation_returns_409_when_session_not_completed(
    db_session: Session,
) -> None:
    owner_username = "owner-user"
    session = _seed_session(
        db_session, owner_username=owner_username, state=SessionState.ACTIVE
    )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/sessions/{session.id}/explanation",
            headers={
                **_auth_header(token=f"local:{owner_username}"),
                "Idempotency-Key": "explain-key-2",
            },
            json=_request_body(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "SESSION_NOT_READY"


@pytest.mark.usefixtures("engine")
def test_learner_explanation_returns_500_when_session_metadata_incomplete(
    db_session: Session,
) -> None:
    owner_username = "owner-user"
    session = _seed_session(
        db_session,
        owner_username=owner_username,
        state=SessionState.COMPLETED,
        lab_id=None,
    )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/sessions/{session.id}/explanation",
            headers={
                **_auth_header(token=f"local:{owner_username}"),
                "Idempotency-Key": "explain-key-3",
            },
            json=_request_body(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "SESSION_METADATA_INCOMPLETE"


@pytest.mark.usefixtures("engine")
def test_learner_explanation_returns_500_when_session_metadata_invalid(
    db_session: Session,
) -> None:
    owner_username = "owner-user"
    session = _seed_session(
        db_session,
        owner_username=owner_username,
        state=SessionState.COMPLETED,
        lab_difficulty="hard",
    )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/sessions/{session.id}/explanation",
            headers={
                **_auth_header(token=f"local:{owner_username}"),
                "Idempotency-Key": "explain-key-4",
            },
            json=_request_body(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "SESSION_METADATA_INVALID"


@pytest.mark.usefixtures("engine")
def test_learner_explanation_returns_400_for_invalid_explanation_payload(
    db_session: Session,
) -> None:
    owner_username = "owner-user"
    session = _seed_session(
        db_session, owner_username=owner_username, state=SessionState.COMPLETED
    )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/sessions/{session.id}/explanation",
            headers={
                **_auth_header(token=f"local:{owner_username}"),
                "Idempotency-Key": "explain-key-5",
            },
            json=_request_body(explanation=" " * 20),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_EXPLANATION"


@pytest.mark.usefixtures("engine")
def test_learner_explanation_idempotent_replay_returns_same_result_without_duplicate_side_effects(
    db_session: Session,
) -> None:
    owner_username = "owner-user"
    session = _seed_session(
        db_session, owner_username=owner_username, state=SessionState.COMPLETED
    )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        first = client.post(
            f"/api/v1/sessions/{session.id}/explanation",
            headers={
                **_auth_header(token=f"local:{owner_username}"),
                "Idempotency-Key": "explain-key-6",
            },
            json=_request_body(),
        )
        second = client.post(
            f"/api/v1/sessions/{session.id}/explanation",
            headers={
                **_auth_header(token=f"local:{owner_username}"),
                "Idempotency-Key": "explain-key-6",
            },
            json=_request_body(),
        )
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["explanation_id"] == first.json()["explanation_id"]

    explanation_count = db_session.execute(
        select(func.count()).select_from(LearnerExplanationModel)
    ).scalar_one()
    assert explanation_count == 1

    trace_count = db_session.execute(
        select(func.count())
        .select_from(TraceEventModel)
        .where(
            TraceEventModel.session_id == session.id,
            TraceEventModel.event_type == "LEARNER_EXPLANATION_SUBMITTED",
        )
    ).scalar_one()
    assert trace_count == 1

    evaluate_outbox_count = db_session.execute(
        select(func.count())
        .select_from(OutboxEventModel)
        .where(
            OutboxEventModel.aggregate_id == session.id,
            OutboxEventModel.event_type == "session.evaluate.requested.v1",
        )
    ).scalar_one()
    assert evaluate_outbox_count == 1
