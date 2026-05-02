import asyncio
import threading
from datetime import datetime, timezone
from collections.abc import AsyncIterator, Callable
from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect

from apps.contracts.src.schemas import (
    AttackEmailSentEvent,
    MaliciousEmailReadEvent,
    RuntimeStreamEvent,
    TokenDisclosedEvent,
    ToolCallFailedEvent,
    ToolCallRequestedEvent,
    ToolCallSucceededEvent,
    TextChunkEvent,
    TurnCompletedEvent,
    TurnFailedEvent,
    TurnStartedEvent,
)
from apps.contracts.src.lab_secrets import LAB1_DISCLOSED_SECRET_KIND
from apps.control_plane.src.application.runtime.types import (
    RunTurnInput,
    ReadRuntimeFileInput,
    ReadRuntimeFileOutput,
)
from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.models import (
    SessionModel,
    SessionRuntimeBindingModel,
    TraceEventModel,
)
from apps.control_plane.src.interfaces.http.dependencies import (
    get_authority_bulletin_classifier,
    get_runtime_client_factory,
    get_ws_session_manager,
)
from apps.control_plane.src.interfaces.http.main import app
from apps.control_plane.src.interfaces.http.session_manager import (
    WebSocketSessionManager,
)


def _override_db_session(db_session: Session):
    def _dependency_override():
        try:
            yield db_session
        finally:
            pass

    return _dependency_override


class _FakeRuntimeClient:
    def __init__(
        self,
        stream_factory: Callable[[RunTurnInput], AsyncIterator[RuntimeStreamEvent]],
    ) -> None:
        self._stream_factory = stream_factory

    async def run_turn(self, input: RunTurnInput) -> Any:
        _ = input
        raise NotImplementedError

    def run_turn_stream(self, input: RunTurnInput) -> AsyncIterator[RuntimeStreamEvent]:
        return self._stream_factory(input)

    async def inject_email(self, input: Any) -> None:
        _ = input

    async def read_runtime_file(
        self, input: ReadRuntimeFileInput
    ) -> ReadRuntimeFileOutput:
        _ = input
        return ReadRuntimeFileOutput(path="/var/secure/ops_runbook.md", content=None)


class _CapturingRuntimeClient(_FakeRuntimeClient):
    def __init__(
        self,
        stream_factory: Callable[[RunTurnInput], AsyncIterator[RuntimeStreamEvent]],
    ) -> None:
        super().__init__(stream_factory=stream_factory)
        self.inputs: list[RunTurnInput] = []

    def run_turn_stream(self, input: RunTurnInput) -> AsyncIterator[RuntimeStreamEvent]:
        self.inputs.append(input)
        return super().run_turn_stream(input)


class _FakeAuthorityBulletinClassifier:
    def __init__(
        self,
        *,
        passed: bool,
        signer_name: str | None,
        runbook_action_type: Literal["prod_db_delete", "other"] | None = None,
        destructive_db_delete: bool | None = None,
    ) -> None:
        self._passed = passed
        self._signer_name = signer_name
        self._runbook_action_type: Literal["prod_db_delete", "other"] | None = (
            runbook_action_type
        )
        self._destructive_db_delete = destructive_db_delete

    async def classify_prompt(self, *, input: Any) -> Any:
        from apps.control_plane.src.application.prompt_classification.types import (
            AuthorityBulletinClassificationResult,
        )

        _ = input
        return AuthorityBulletinClassificationResult(
            is_authority_bulletin=self._passed,
            signer_name=self._signer_name,
            runbook_action_type=self._runbook_action_type,
            destructive_db_delete=self._destructive_db_delete,
            confidence=0.9,
            reason="test",
            provider="test",
            model="test-model",
        )


class _FakeRuntimeClientFactory:
    def __init__(self, fake_client: _FakeRuntimeClient) -> None:
        self._fake_client = fake_client
        self.created_base_urls: list[str] = []

    def create(self, *, base_url: str) -> _FakeRuntimeClient:
        self.created_base_urls.append(base_url)
        return self._fake_client


def _override_runtime_client(fake_client: _FakeRuntimeClient):
    factory = _FakeRuntimeClientFactory(fake_client=fake_client)

    def _dependency_override() -> _FakeRuntimeClientFactory:
        return factory

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
    db_session.add(
        SessionRuntimeBindingModel(
            session_id=session.id,
            runtime_kind="k8s_pod",
            base_url="http://runtime.test.local:8000",
            auth_token_ref=None,
            status="ready",
            last_error=None,
        )
    )
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
    db_session.add(
        SessionRuntimeBindingModel(
            session_id=session.id,
            runtime_kind="k8s_pod",
            base_url="http://runtime.test.local:8000",
            auth_token_ref=None,
            status="ready",
            last_error=None,
        )
    )
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


def _default_runtime_client() -> _FakeRuntimeClient:
    async def _stream(_input: RunTurnInput) -> AsyncIterator[RuntimeStreamEvent]:
        if False:
            yield TurnStartedEvent(type="turn_started")

    return _FakeRuntimeClient(stream_factory=_stream)


@pytest.mark.usefixtures("engine")
def test_stream_owner_can_connect_and_get_initial_session_status(
    db_session: Session,
) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_runtime_client_factory] = _override_runtime_client(
        _default_runtime_client()
    )
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
    app.dependency_overrides[get_runtime_client_factory] = _override_runtime_client(
        _default_runtime_client()
    )
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
    app.dependency_overrides[get_runtime_client_factory] = _override_runtime_client(
        _default_runtime_client()
    )
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
    app.dependency_overrides[get_runtime_client_factory] = _override_runtime_client(
        _default_runtime_client()
    )
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
    app.dependency_overrides[get_runtime_client_factory] = _override_runtime_client(
        _default_runtime_client()
    )
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
) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)

    async def _stream(_input: RunTurnInput) -> AsyncIterator[RuntimeStreamEvent]:
        yield TurnStartedEvent(type="turn_started")
        yield TextChunkEvent(
            type="text_chunk", content="response chunk", chunk_index=0, final=True
        )
        yield TurnCompletedEvent(type="turn_completed", duration_ms=5, chunks_emitted=1)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_runtime_client_factory] = _override_runtime_client(
        _FakeRuntimeClient(stream_factory=_stream)
    )
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
def test_user_prompt_uses_session_runtime_binding_base_url_not_global_config(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)
    binding_base_url = "http://binding.runtime.local:8000"

    binding = db_session.get(SessionRuntimeBindingModel, session.id)
    assert binding is not None
    binding.base_url = binding_base_url
    db_session.flush()

    monkeypatch.setenv("RUNTIME_BASE_URL", "http://global.runtime.invalid:9999")

    async def _stream(_input: RunTurnInput) -> AsyncIterator[RuntimeStreamEvent]:
        yield TurnStartedEvent(type="turn_started")
        yield TextChunkEvent(
            type="text_chunk", content="response chunk", chunk_index=0, final=True
        )
        yield TurnCompletedEvent(type="turn_completed", duration_ms=5, chunks_emitted=1)

    fake_factory = _FakeRuntimeClientFactory(
        fake_client=_FakeRuntimeClient(stream_factory=_stream)
    )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_runtime_client_factory] = lambda: fake_factory
    try:
        client = TestClient(app)
        with client.websocket_connect(
            f"/api/v1/sessions/{session.id}/stream",
            headers=_auth_headers(token=f"local:{owner_username}"),
        ) as ws:
            _ = ws.receive_json()  # initial SESSION_STATUS
            ws.send_json(_user_prompt_message(session.id, "hello"))
            _ = ws.receive_json()  # TRACE_EVENT TURN_STARTED
            _ = ws.receive_json()  # TRACE_EVENT MODEL_REQUEST_STARTED
            msg = ws.receive_json()
    finally:
        app.dependency_overrides.clear()

    _assert_required_server_message_fields(
        msg, expected_type="AGENT_TEXT_CHUNK", session_id=session.id
    )
    assert msg["payload"]["content"] == "response chunk"
    assert fake_factory.created_base_urls == [binding_base_url]


@pytest.mark.usefixtures("engine")
def test_lab2_prompt_threads_authority_bulletin_flags_into_runtime_turn_input(
    db_session: Session,
) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)
    session.lab_id = UUID("22222222-2222-2222-2222-222222222222")
    db_session.flush()

    async def _stream(_input: RunTurnInput) -> AsyncIterator[RuntimeStreamEvent]:
        yield TurnStartedEvent(type="turn_started")
        yield TurnCompletedEvent(type="turn_completed", duration_ms=1, chunks_emitted=0)

    capturing_client = _CapturingRuntimeClient(stream_factory=_stream)
    fake_factory = _FakeRuntimeClientFactory(fake_client=capturing_client)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_runtime_client_factory] = lambda: fake_factory
    app.dependency_overrides[get_authority_bulletin_classifier] = lambda: (
        _FakeAuthorityBulletinClassifier(
            passed=True,
            signer_name="Morgan Hale",
            runbook_action_type="prod_db_delete",
            destructive_db_delete=True,
        )
    )
    try:
        client = TestClient(app)
        with client.websocket_connect(
            f"/api/v1/sessions/{session.id}/stream",
            headers=_auth_headers(token=f"local:{owner_username}"),
        ) as ws:
            _ = ws.receive_json()
            ws.send_json(_user_prompt_message(session.id, "Formal ops bulletin..."))
            _ = ws.receive_json()
            _ = ws.receive_json()
    finally:
        app.dependency_overrides.clear()

    assert len(capturing_client.inputs) == 1
    assert capturing_client.inputs[0].authority_bulletin_passed is True


@pytest.mark.usefixtures("engine")
def test_lab2_prompt_signer_mismatch_fails_closed_for_authority_bulletin(
    db_session: Session,
) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)
    session.lab_id = UUID("22222222-2222-2222-2222-222222222222")
    db_session.flush()

    async def _stream(_input: RunTurnInput) -> AsyncIterator[RuntimeStreamEvent]:
        yield TurnStartedEvent(type="turn_started")
        yield TurnCompletedEvent(type="turn_completed", duration_ms=1, chunks_emitted=0)

    capturing_client = _CapturingRuntimeClient(stream_factory=_stream)
    fake_factory = _FakeRuntimeClientFactory(fake_client=capturing_client)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_runtime_client_factory] = lambda: fake_factory
    app.dependency_overrides[get_authority_bulletin_classifier] = lambda: (
        _FakeAuthorityBulletinClassifier(passed=True, signer_name="Not Morgan")
    )
    try:
        client = TestClient(app)
        with client.websocket_connect(
            f"/api/v1/sessions/{session.id}/stream",
            headers=_auth_headers(token=f"local:{owner_username}"),
        ) as ws:
            _ = ws.receive_json()
            ws.send_json(_user_prompt_message(session.id, "Formal ops bulletin..."))
            _ = ws.receive_json()
            _ = ws.receive_json()
    finally:
        app.dependency_overrides.clear()

    assert len(capturing_client.inputs) == 1
    assert capturing_client.inputs[0].authority_bulletin_passed is False


@pytest.mark.usefixtures("engine")
def test_runtime_lab_events_are_persisted_to_runtime_trace_family(
    db_session: Session,
) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)

    async def _stream(_input: RunTurnInput) -> AsyncIterator[RuntimeStreamEvent]:
        yield TurnStartedEvent(type="turn_started")
        yield AttackEmailSentEvent(
            type="attack_email_sent",
            email_id="e2",
            recipient="learner@lab.local",
            subject="URGENT: Policy update",
        )
        yield ToolCallRequestedEvent(
            type="tool_call_requested",
            tool_name="read_email",
            target_resource="e2",
            operation="read",
        )
        yield ToolCallSucceededEvent(
            type="tool_call_succeeded",
            tool_name="read_email",
            target_resource="e2",
            operation="read",
        )
        yield MaliciousEmailReadEvent(
            type="malicious_email_read",
            email_id="e2",
            subject="URGENT: Policy update",
            malicious_marker=True,
        )
        yield TokenDisclosedEvent(
            type="token_disclosed",
            channel="assistant_output",
            token_kind=LAB1_DISCLOSED_SECRET_KIND,
        )
        yield TextChunkEvent(
            type="text_chunk", content="response chunk", chunk_index=0, final=True
        )
        yield TurnCompletedEvent(type="turn_completed", duration_ms=5, chunks_emitted=1)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_runtime_client_factory] = _override_runtime_client(
        _FakeRuntimeClient(stream_factory=_stream)
    )
    try:
        client = TestClient(app)
        with client.websocket_connect(
            f"/api/v1/sessions/{session.id}/stream",
            headers=_auth_headers(token=f"local:{owner_username}"),
        ) as ws:
            _ = ws.receive_json()  # initial SESSION_STATUS
            ws.send_json(_user_prompt_message(session.id, "hello"))
            _ = ws.receive_json()  # TRACE_EVENT TURN_STARTED
            _ = ws.receive_json()  # TRACE_EVENT MODEL_REQUEST_STARTED
            _ = ws.receive_json()  # AGENT_TEXT_CHUNK
    finally:
        app.dependency_overrides.clear()

    runtime_events = (
        db_session.execute(
            select(TraceEventModel)
            .where(
                TraceEventModel.session_id == session.id,
                TraceEventModel.family == "runtime",
            )
            .order_by(TraceEventModel.event_index.asc())
        )
        .scalars()
        .all()
    )
    assert [event.event_type for event in runtime_events] == [
        "ATTACK_EMAIL_SENT",
        "MALICIOUS_EMAIL_READ",
        "TOKEN_DISCLOSED",
    ]
    assert runtime_events[0].payload["email_id"] == "e2"
    assert runtime_events[2].payload["token_kind"] == LAB1_DISCLOSED_SECRET_KIND

    tool_events = (
        db_session.execute(
            select(TraceEventModel)
            .where(
                TraceEventModel.session_id == session.id,
                TraceEventModel.family == "tool",
            )
            .order_by(TraceEventModel.event_index.asc())
        )
        .scalars()
        .all()
    )
    assert [event.event_type for event in tool_events] == [
        "TOOL_CALL_REQUESTED",
        "TOOL_CALL_SUCCEEDED",
    ]
    assert tool_events[0].payload["tool_name"] == "read_email"


@pytest.mark.usefixtures("engine")
def test_tool_call_payload_fields_are_propagated_to_trace_events(
    db_session: Session,
) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)

    async def _stream(_input: RunTurnInput) -> AsyncIterator[RuntimeStreamEvent]:
        yield TurnStartedEvent(type="turn_started")
        yield ToolCallRequestedEvent(
            type="tool_call_requested",
            tool_name="write_memory",
            target_resource="vendor_profile_memory",
            operation="write",
            memory_type="vendor_profile_memory",
            provenance_trust="untrusted",
            source_artifact_id="email-urgent-remit",
            source_artifact_type="vendor_email",
        )
        yield ToolCallSucceededEvent(
            type="tool_call_succeeded",
            tool_name="retrieve_memory",
            target_resource="vendor_profile_memory",
            operation="retrieve_during_payment",
            invoice_id="inv-acme-2026-041",
            vendor_name="Acme Corp",
            vendor_id="vendor-acme-001",
            retrieved_memory_references=["email-urgent-remit", "ticket-42"],
        )
        yield ToolCallFailedEvent(
            type="tool_call_failed",
            tool_name="pay_invoice",
            target_resource="inv-acme-2026-041",
            operation="pay",
            error_code="PAYMENT_REJECTED",
            invoice_id="inv-acme-2026-041",
            vendor_name="Acme Corp",
            amount=14850.75,
            account_number="ACCT-4421",
        )
        yield TextChunkEvent(
            type="text_chunk", content="response chunk", chunk_index=0, final=True
        )
        yield TurnCompletedEvent(type="turn_completed", duration_ms=5, chunks_emitted=1)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_runtime_client_factory] = _override_runtime_client(
        _FakeRuntimeClient(stream_factory=_stream)
    )
    try:
        client = TestClient(app)
        with client.websocket_connect(
            f"/api/v1/sessions/{session.id}/stream",
            headers=_auth_headers(token=f"local:{owner_username}"),
        ) as ws:
            _ = ws.receive_json()  # initial SESSION_STATUS
            ws.send_json(_user_prompt_message(session.id, "hello"))
            _ = ws.receive_json()  # TRACE_EVENT TURN_STARTED
            _ = ws.receive_json()  # TRACE_EVENT MODEL_REQUEST_STARTED
            _ = ws.receive_json()  # AGENT_TEXT_CHUNK
    finally:
        app.dependency_overrides.clear()

    tool_events = (
        db_session.execute(
            select(TraceEventModel)
            .where(
                TraceEventModel.session_id == session.id,
                TraceEventModel.family == "tool",
            )
            .order_by(TraceEventModel.event_index.asc())
        )
        .scalars()
        .all()
    )

    assert [event.event_type for event in tool_events] == [
        "TOOL_CALL_REQUESTED",
        "TOOL_CALL_SUCCEEDED",
        "TOOL_CALL_FAILED",
    ]
    assert tool_events[0].payload == {
        "type": "tool_call_requested",
        "tool_name": "write_memory",
        "target_resource": "vendor_profile_memory",
        "operation": "write",
        "memory_type": "vendor_profile_memory",
        "provenance_trust": "untrusted",
        "source_artifact_id": "email-urgent-remit",
        "source_artifact_type": "vendor_email",
    }
    assert tool_events[1].payload == {
        "type": "tool_call_succeeded",
        "tool_name": "retrieve_memory",
        "target_resource": "vendor_profile_memory",
        "operation": "retrieve_during_payment",
        "invoice_id": "inv-acme-2026-041",
        "vendor_name": "Acme Corp",
        "vendor_id": "vendor-acme-001",
        "retrieved_memory_references": ["email-urgent-remit", "ticket-42"],
    }
    assert tool_events[2].payload == {
        "type": "tool_call_failed",
        "tool_name": "pay_invoice",
        "target_resource": "inv-acme-2026-041",
        "operation": "pay",
        "error_code": "PAYMENT_REJECTED",
        "invoice_id": "inv-acme-2026-041",
        "vendor_name": "Acme Corp",
        "amount": 14850.75,
        "account_number": "ACCT-4421",
    }


@pytest.mark.usefixtures("engine")
def test_user_prompt_overlapping_turn_is_denied(
    db_session: Session,
) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)
    started = threading.Event()

    async def _stream(_input: RunTurnInput) -> AsyncIterator[RuntimeStreamEvent]:
        started.set()
        yield TurnStartedEvent(type="turn_started")
        await asyncio.sleep(0.25)
        yield TextChunkEvent(
            type="text_chunk", content="done", chunk_index=0, final=True
        )
        yield TurnCompletedEvent(
            type="turn_completed", duration_ms=10, chunks_emitted=1
        )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_runtime_client_factory] = _override_runtime_client(
        _FakeRuntimeClient(stream_factory=_stream)
    )
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
    app.dependency_overrides[get_runtime_client_factory] = _override_runtime_client(
        _default_runtime_client()
    )
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
) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)

    def _stream(_input: RunTurnInput) -> AsyncIterator[RuntimeStreamEvent]:
        raise RuntimeError("boom")

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_runtime_client_factory] = _override_runtime_client(
        _FakeRuntimeClient(stream_factory=_stream)
    )
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
) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)

    async def _stream(_input: RunTurnInput) -> AsyncIterator[RuntimeStreamEvent]:
        yield TurnStartedEvent(type="turn_started")
        yield TurnFailedEvent(
            type="turn_failed",
            error_code="provider_failure",
            message="provider failed before first chunk",
            retryable=True,
        )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_runtime_client_factory] = _override_runtime_client(
        _FakeRuntimeClient(stream_factory=_stream)
    )
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
    assert msg["payload"]["message"] == "provider failed before first chunk"

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
) -> None:
    owner_username = "stream-owner"
    session = _seed_active_session(db_session, owner_username=owner_username)

    async def _stream(_input: RunTurnInput) -> AsyncIterator[RuntimeStreamEvent]:
        yield TurnStartedEvent(type="turn_started")
        yield TextChunkEvent(
            type="text_chunk", content="first", chunk_index=0, final=False
        )

    class _TimeoutOnChunkSessionManager(WebSocketSessionManager):
        async def send_to(self, websocket: Any, message: Any) -> None:
            if getattr(message, "type", None) == "AGENT_TEXT_CHUNK":
                raise asyncio.TimeoutError()
            await super().send_to(websocket=websocket, message=message)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_runtime_client_factory] = _override_runtime_client(
        _FakeRuntimeClient(stream_factory=_stream)
    )
    app.dependency_overrides[get_ws_session_manager] = lambda: (
        _TimeoutOnChunkSessionManager()
    )
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
