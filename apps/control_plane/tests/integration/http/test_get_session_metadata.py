from uuid import UUID, NAMESPACE_URL, uuid4, uuid5

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.models import SessionModel
from apps.control_plane.src.interfaces.http.main import app
from apps.control_plane.src.infrastructure.persistence.db import get_db_session


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


def test_get_session_metadata_returns_200(db_session: Session) -> None:
    session_id = uuid4()
    lab_id = uuid4()
    lab_version_id = uuid4()
    owner_username = "owner-user"

    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=lab_id,
            lab_version_id=lab_version_id,
            owner_user_id=_owner_user_id(owner_username),
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
        response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert "session" in body
    session = body["session"]

    assert session["id"] == str(session_id)
    assert session["lab_id"] == str(lab_id)
    assert session["lab_version_id"] == str(lab_version_id)
    assert session["state"] == SessionState.ACTIVE.value
    assert session["runtime_substate"] == "WAITING_FOR_INPUT"
    assert session["resume_mode"] == "hot_resume"
    assert session["interactive"] is True
    assert session["created_at"] is not None
    assert session["started_at"] is None
    assert session["ended_at"] is None


def test_get_session_metadata_returns_404_for_missing(db_session: Session) -> None:
    missing_id = uuid4()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions/{missing_id}",
            headers=_auth_header(token="local:any-user"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "SESSION_NOT_FOUND"
    assert body["error"]["message"] == "Session not found"
    assert body["error"]["retryable"] is False
    assert body["error"]["details"]["session_id"] == str(missing_id)


def test_get_session_metadata_returns_403_for_non_owner(db_session: Session) -> None:
    session_id = uuid4()
    owner_username = "owner-user"
    requester_username = "different-user"

    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=uuid4(),
            lab_version_id=uuid4(),
            owner_user_id=_owner_user_id(owner_username),
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
        response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{requester_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "FORBIDDEN"
    assert body["error"]["retryable"] is False


def test_get_session_metadata_returns_200_for_admin_non_owner(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "owner-user"

    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=uuid4(),
            lab_version_id=uuid4(),
            owner_user_id=_owner_user_id(owner_username),
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
        response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token="local:admin-user:admin"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
