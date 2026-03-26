import asyncio
import threading
import time
from datetime import datetime, timezone
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

from apps.agent_harness.src.application.session_loop.types import (
    HarnessChunk,
    HarnessFailure,
    HarnessTurnResult,
)
from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.models import (
    SessionModel,
    TraceEventModel,
)
import apps.control_plane.src.interfaces.http.main as main_module
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


def _seed_session(
    db_session: Session,
    owner_username: str,
    *,
    state: SessionState,
    runtime_substate: str | None,
) -> SessionModel:
    session = SessionModel(
        id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        owner_user_id=_owner_user_id(owner_username),
        state=state.value,
        runtime_substate=runtime_substate,
        resume_mode="hot_resume",
        last_transition_actor="seed",
        last_transition_reason=None,
    )
    db_session.add(session)
    db_session.flush()
    return session


def _user_prompt_message(session_id: UUID, content: str) -> dict[str, object]:
    return {
        "type": "USER_PROMPT",
        "session_id": str(session_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": {"content": content},
    }


def _assert_required_server_message_fields(
    msg: dict[str, Any], *, expected_type: str, session_id: UUID
) -> None:
    assert msg["type"] == expected_type
    assert msg["session_id"] == str(session_id)
    assert "timestamp" in msg
    assert "payload" in msg


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


@pytest.mark.usefixtures("engine")
def test_user_prompt_is_accepted_for_interactive_session(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)

    def _fake_run_local_one_turn(_turn: object) -> HarnessTurnResult:
        return HarnessTurnResult(
            chunks=[
                HarnessChunk(content="response chunk", final=True),
            ]
        )

    monkeypatch.setattr(main_module, "run_local_one_turn", _fake_run_local_one_turn)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        with client.websocket_connect(
            f"/api/v1/sessions/{session.id}/stream",
            headers=_auth_headers(token=f"local:{owner_username}"),
        ) as ws:
            _ = ws.receive_json()  # initial SESSION_STATUS
            ws.send_json(_user_prompt_message(session.id, "hello"))
            trace_msg_1 = ws.receive_json()
            trace_msg_2 = ws.receive_json()
            msg = ws.receive_json()
    finally:
        app.dependency_overrides.clear()

    _assert_required_server_message_fields(
        trace_msg_1, expected_type="TRACE_EVENT", session_id=session.id
    )
    assert trace_msg_1["payload"]["event_code"] == "TURN_STARTED"

    _assert_required_server_message_fields(
        trace_msg_2, expected_type="TRACE_EVENT", session_id=session.id
    )
    assert trace_msg_2["payload"]["event_code"] == "MODEL_REQUEST_STARTED"

    _assert_required_server_message_fields(
        msg, expected_type="AGENT_TEXT_CHUNK", session_id=session.id
    )
    assert msg["payload"]["content"] == "response chunk"
    assert msg["payload"]["final"] is True

    trace_event = db_session.execute(
        select(TraceEventModel).where(
            TraceEventModel.session_id == session.id,
            TraceEventModel.family == "learner",
            TraceEventModel.event_type == "USER_PROMPT_SUBMITTED",
        )
    ).scalar_one()
    assert trace_event.actor_user_id == _owner_user_id(owner_username)
    payload = trace_event.payload
    assert payload["message_type"] == "USER_PROMPT"
    assert payload["content"] == "hello"

    model_events = (
        db_session.execute(
            select(TraceEventModel)
            .where(
                TraceEventModel.session_id == session.id,
                TraceEventModel.family == "model",
            )
            .order_by(TraceEventModel.event_index.asc())
        )
        .scalars()
        .all()
    )
    assert [event.event_type for event in model_events] == [
        "MODEL_TURN_STARTED",
        "MODEL_TURN_COMPLETED",
    ]


@pytest.mark.usefixtures("engine")
def test_user_prompt_overlapping_turn_is_denied(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)
    started = threading.Event()

    def _slow_run_local_one_turn(_turn: object) -> HarnessTurnResult:
        started.set()
        time.sleep(0.25)
        return HarnessTurnResult(
            chunks=[HarnessChunk(content="done", final=True)],
        )

    monkeypatch.setattr(main_module, "run_local_one_turn", _slow_run_local_one_turn)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        with client.websocket_connect(
            f"/api/v1/sessions/{session.id}/stream",
            headers=_auth_headers(token=f"local:{owner_username}"),
        ) as ws1:
            with client.websocket_connect(
                f"/api/v1/sessions/{session.id}/stream",
                headers=_auth_headers(token=f"local:{owner_username}"),
            ) as ws2:
                _ = ws1.receive_json()  # initial SESSION_STATUS
                _ = ws2.receive_json()  # initial SESSION_STATUS

                ws1.send_json(_user_prompt_message(session.id, "first"))
                _ = ws1.receive_json()  # TRACE_EVENT TURN_STARTED
                _ = ws1.receive_json()  # TRACE_EVENT MODEL_REQUEST_STARTED
                assert started.wait(timeout=1.0)

                ws2.send_json(_user_prompt_message(session.id, "second"))
                msg = ws2.receive_json()
    finally:
        app.dependency_overrides.clear()

    _assert_required_server_message_fields(
        msg, expected_type="POLICY_DENIAL", session_id=session.id
    )
    assert msg["payload"]["reason_code"] == "TURN_IN_PROGRESS"


@pytest.mark.usefixtures("engine")
def test_user_prompt_non_interactive_session_is_denied(
    db_session: Session,
) -> None:
    owner_username = "stream-owner"
    session = _seed_session(
        db_session,
        owner_username=owner_username,
        state=SessionState.COMPLETED,
        runtime_substate="FINISHED",
    )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        with client.websocket_connect(
            f"/api/v1/sessions/{session.id}/stream",
            headers=_auth_headers(token=f"local:{owner_username}"),
        ) as ws:
            _ = ws.receive_json()  # initial SESSION_STATUS
            ws.send_json(_user_prompt_message(session.id, "should fail"))
            msg = ws.receive_json()
    finally:
        app.dependency_overrides.clear()

    _assert_required_server_message_fields(
        msg, expected_type="POLICY_DENIAL", session_id=session.id
    )
    assert msg["payload"]["reason_code"] == "SESSION_NOT_INTERACTIVE"


@pytest.mark.usefixtures("engine")
def test_user_prompt_internal_failure_emits_system_error(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)

    def _crash_run_local_one_turn(_turn: object) -> HarnessTurnResult:
        raise RuntimeError("boom")

    monkeypatch.setattr(main_module, "run_local_one_turn", _crash_run_local_one_turn)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        with client.websocket_connect(
            f"/api/v1/sessions/{session.id}/stream",
            headers=_auth_headers(token=f"local:{owner_username}"),
        ) as ws:
            _ = ws.receive_json()  # initial SESSION_STATUS
            ws.send_json(_user_prompt_message(session.id, "crash"))
            _ = ws.receive_json()  # TRACE_EVENT TURN_STARTED
            _ = ws.receive_json()  # TRACE_EVENT MODEL_REQUEST_STARTED
            msg = ws.receive_json()
    finally:
        app.dependency_overrides.clear()

    _assert_required_server_message_fields(
        msg, expected_type="SYSTEM_ERROR", session_id=session.id
    )
    assert msg["payload"]["error_code"] == "INTERNAL_ERROR"
    assert isinstance(msg["payload"]["message"], str)


@pytest.mark.usefixtures("engine")
def test_user_prompt_failure_before_first_chunk_emits_stable_system_error(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)

    def _failed_before_first_chunk(_turn: object) -> HarnessTurnResult:
        return HarnessTurnResult(
            chunks=[],
            failure=HarnessFailure(
                code="provider_failure",
                message="provider failed before first chunk",
                details=None,
            ),
        )

    monkeypatch.setattr(main_module, "run_local_one_turn", _failed_before_first_chunk)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        with client.websocket_connect(
            f"/api/v1/sessions/{session.id}/stream",
            headers=_auth_headers(token=f"local:{owner_username}"),
        ) as ws:
            _ = ws.receive_json()  # initial SESSION_STATUS
            ws.send_json(_user_prompt_message(session.id, "trigger failure"))
            _ = ws.receive_json()  # TRACE_EVENT TURN_STARTED
            _ = ws.receive_json()  # TRACE_EVENT MODEL_REQUEST_STARTED
            msg = ws.receive_json()
    finally:
        app.dependency_overrides.clear()

    _assert_required_server_message_fields(
        msg, expected_type="SYSTEM_ERROR", session_id=session.id
    )
    assert msg["payload"]["error_code"] == "TURN_FAILED_BEFORE_FIRST_CHUNK"
    assert (
        msg["payload"]["message"]
        == "The assistant failed before responding. Please resend your prompt."
    )

    model_events = (
        db_session.execute(
            select(TraceEventModel)
            .where(
                TraceEventModel.session_id == session.id,
                TraceEventModel.family == "model",
            )
            .order_by(TraceEventModel.event_index.asc())
        )
        .scalars()
        .all()
    )
    assert [event.event_type for event in model_events] == [
        "MODEL_TURN_STARTED",
        "MODEL_TURN_FAILED",
    ]
    failed_payload = model_events[-1].payload
    assert failed_payload["error_code"] == "TURN_FAILED_BEFORE_FIRST_CHUNK"


@pytest.mark.usefixtures("engine")
def test_user_prompt_mid_stream_send_timeout_emits_stable_system_error(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)

    def _successful_turn(_turn: object) -> HarnessTurnResult:
        return HarnessTurnResult(
            chunks=[HarnessChunk(content="first", final=False)],
            failure=None,
        )

    original_send_to = main_module.ws_manager.send_to

    async def _timeout_on_agent_chunk(websocket: Any, message: Any) -> None:
        if getattr(message, "type", None) == "AGENT_TEXT_CHUNK":
            raise asyncio.TimeoutError()
        await original_send_to(websocket, message)

    monkeypatch.setattr(main_module, "run_local_one_turn", _successful_turn)
    monkeypatch.setattr(main_module.ws_manager, "send_to", _timeout_on_agent_chunk)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        with client.websocket_connect(
            f"/api/v1/sessions/{session.id}/stream",
            headers=_auth_headers(token=f"local:{owner_username}"),
        ) as ws:
            _ = ws.receive_json()  # initial SESSION_STATUS
            ws.send_json(_user_prompt_message(session.id, "trigger timeout"))
            _ = ws.receive_json()  # TRACE_EVENT TURN_STARTED
            _ = ws.receive_json()  # TRACE_EVENT MODEL_REQUEST_STARTED
            msg = ws.receive_json()
    finally:
        app.dependency_overrides.clear()

    _assert_required_server_message_fields(
        msg, expected_type="SYSTEM_ERROR", session_id=session.id
    )
    assert msg["payload"]["error_code"] == "TURN_FAILED_MID_STREAM"
    assert (
        msg["payload"]["message"]
        == "The response was interrupted. You can retry to continue."
    )

    model_events = (
        db_session.execute(
            select(TraceEventModel)
            .where(
                TraceEventModel.session_id == session.id,
                TraceEventModel.family == "model",
            )
            .order_by(TraceEventModel.event_index.asc())
        )
        .scalars()
        .all()
    )
    assert [event.event_type for event in model_events] == [
        "MODEL_TURN_STARTED",
        "MODEL_TURN_FAILED",
    ]
    failed_payload = model_events[-1].payload
    assert failed_payload["error_code"] == "TURN_FAILED_MID_STREAM"
