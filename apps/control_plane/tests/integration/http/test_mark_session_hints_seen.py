from datetime import datetime, timedelta, timezone
from uuid import UUID, NAMESPACE_URL, uuid4, uuid5

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.models import (
    SessionHintModel,
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


def test_mark_session_hints_seen_owner_updates_unlocked_unseen(
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
            SessionHintModel(
                id=uuid4(),
                session_id=session_id,
                hint_key="hint_1",
                text="h1",
                sort_order=0,
                status="unlocked",
                unlock_at=now - timedelta(minutes=2),
                unlocked_at=now - timedelta(minutes=1),
                seen_at=None,
            ),
            SessionHintModel(
                id=uuid4(),
                session_id=session_id,
                hint_key="hint_2",
                text="h2",
                sort_order=1,
                status="unlocked",
                unlock_at=now - timedelta(minutes=2),
                unlocked_at=now - timedelta(minutes=1),
                seen_at=now - timedelta(seconds=10),
            ),
            SessionHintModel(
                id=uuid4(),
                session_id=session_id,
                hint_key="hint_3",
                text="h3",
                sort_order=2,
                status="pending",
                unlock_at=now + timedelta(minutes=5),
                unlocked_at=None,
                seen_at=None,
            ),
        ]
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/sessions/{session_id}/hints/mark-seen",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["session_id"] == str(session_id)
        assert body["updated_count"] == 1

        metadata = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
        assert metadata.status_code == 200
        assert metadata.json()["session"]["unread_hint_count"] == 0
    finally:
        app.dependency_overrides.clear()


def test_mark_session_hints_seen_forbidden_for_non_owner_non_admin(
    db_session: Session,
) -> None:
    session_id = uuid4()
    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=uuid4(),
            lab_version_id=uuid4(),
            owner_user_id=_owner_user_id("owner-user"),
            state=SessionState.ACTIVE.value,
            runtime_substate="WAITING_FOR_INPUT",
            resume_mode="hot_resume",
            last_transition_actor="seed",
            last_transition_reason=None,
        )
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/sessions/{session_id}/hints/mark-seen",
            headers=_auth_header(token="local:other-user"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_mark_session_hints_seen_returns_404_for_missing(db_session: Session) -> None:
    missing_id = uuid4()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/sessions/{missing_id}/hints/mark-seen",
            headers=_auth_header(token="local:any-user"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "SESSION_NOT_FOUND"
    assert body["error"]["details"]["session_id"] == str(missing_id)
