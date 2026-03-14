from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.models import SessionModel
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


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_active_session(db_session: Session, owner_username: str) -> SessionModel:
    session = SessionModel(
        id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        owner_user_id=_owner_user_id(owner_username),
        state=SessionState.ACTIVE.value,
        runtime_substate="WAITING_FOR_INPUT",
        resume_mode="hot_resume",
        last_transition_actor="seed",
        last_transition_reason=None,
    )
    db_session.add(session)
    db_session.flush()
    return session


@pytest.mark.usefixtures("engine")
def test_stream_owner_can_connect_and_get_initial_session_status(
    db_session: Session,
) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        with client.websocket_connect(
            f"/api/v1/sessions/{session.id}/stream",
            headers=_auth_headers(token=f"local:{owner_username}"),
        ) as ws:
            msg = ws.receive_json()
    finally:
        app.dependency_overrides.clear()

    assert msg["type"] == "SESSION_STATUS"
    assert msg["session_id"] == str(session.id)
    assert "timestamp" in msg
    assert msg["payload"]["state"] == SessionState.ACTIVE.value
    assert msg["payload"]["runtime_substate"] == "WAITING_FOR_INPUT"
    assert msg["payload"]["interactive"] is True


@pytest.mark.usefixtures("engine")
def test_stream_non_owner_is_denied(db_session: Session) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                f"/api/v1/sessions/{session.id}/stream",
                headers=_auth_headers(token="local:not-owner"),
            ):
                pass
    finally:
        app.dependency_overrides.clear()


@pytest.mark.usefixtures("engine")
def test_stream_admin_non_owner_is_allowed(db_session: Session) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        with client.websocket_connect(
            f"/api/v1/sessions/{session.id}/stream",
            headers=_auth_headers(token="local:admin-user:admin"),
        ) as ws:
            msg = ws.receive_json()
    finally:
        app.dependency_overrides.clear()

    assert msg["type"] == "SESSION_STATUS"
    assert msg["session_id"] == str(session.id)


@pytest.mark.usefixtures("engine")
def test_stream_missing_auth_is_denied(db_session: Session) -> None:
    session = _seed_active_session(db_session, owner_username="stream-owner")

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(f"/api/v1/sessions/{session.id}/stream"):
                pass
    finally:
        app.dependency_overrides.clear()


@pytest.mark.usefixtures("engine")
def test_stream_logs_connect_and_disconnect_with_session_context(
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    caplog.set_level(logging.INFO)

    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        with client.websocket_connect(
            f"/api/v1/sessions/{session.id}/stream",
            headers=_auth_headers(token=f"local:{owner_username}"),
        ):
            pass
    finally:
        app.dependency_overrides.clear()

    messages = [record.getMessage().lower() for record in caplog.records]
    session_id = str(session.id)
    assert any("connect" in message and session_id in message for message in messages)
    assert any(
        "disconnect" in message and session_id in message for message in messages
    )
