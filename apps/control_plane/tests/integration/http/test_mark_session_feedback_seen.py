from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.models import (
    SessionFeedbackModel,
    SessionModel,
)
from apps.control_plane.src.interfaces.http.main import app


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


def test_mark_session_feedback_seen_is_idempotent_and_keeps_unread_zero(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "owner-user"
    owner_id = _owner_user_id(owner_username)
    now = datetime.now(timezone.utc)

    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=uuid4(),
            lab_version_id=uuid4(),
            owner_user_id=owner_id,
            state=SessionState.ACTIVE.value,
            runtime_substate="WAITING_FOR_INPUT",
            resume_mode="hot_resume",
            last_transition_actor="seed",
            last_transition_reason=None,
        )
    )
    db_session.flush()
    db_session.add_all(
        [
            SessionFeedbackModel(
                id=uuid4(),
                session_id=session_id,
                feedback_key="lab1_benign_email_not_progressing",
                reason_code="PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS",
                message="This email is benign and did not advance the attack chain.",
                severity="info",
                trigger_event_index=10,
                created_at=now,
                seen_at=None,
                idempotency_key="feedback:test:10",
            ),
            SessionFeedbackModel(
                id=uuid4(),
                session_id=session_id,
                feedback_key="lab1_tool_call_off_path",
                reason_code="TOOL_CALL_OFF_PATH",
                message="This action is valid but off-path.",
                severity="warning",
                trigger_event_index=11,
                created_at=now + timedelta(seconds=1),
                seen_at=now,
                idempotency_key="feedback:test:11",
            ),
        ]
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        first = client.post(
            f"/api/v1/sessions/{session_id}/feedback/mark-seen",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
        second = client.post(
            f"/api/v1/sessions/{session_id}/feedback/mark-seen",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
        metadata = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert first.json()["session_id"] == str(session_id)
    assert first.json()["updated_count"] == 1

    assert second.status_code == 200
    assert second.json()["session_id"] == str(session_id)
    assert second.json()["updated_count"] == 0

    assert metadata.status_code == 200
    assert metadata.json()["session"]["unread_feedback_count"] == 0
