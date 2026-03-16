from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from apps.control_plane.src.interfaces.http.stream_messages import (
    AgentTextChunkPayload,
    PolicyDenialPayload,
    ServerMessageEnvelope,
    SessionStatusPayload,
)


def test_server_message_envelope_accepts_required_fields() -> None:
    session_id = uuid4()
    message = ServerMessageEnvelope(
        type="SESSION_STATUS",
        session_id=session_id,
        timestamp=datetime(2026, 3, 16, 12, 0, 0, tzinfo=UTC),
        payload=SessionStatusPayload(
            state="ACTIVE",
            runtime_substate="RUNNING",
            interactive=True,
        ),
    )

    assert message.type == "SESSION_STATUS"
    assert message.session_id == session_id
    assert message.event_index is None
    assert message.request_id is None
    assert message.correlation_id is None
    assert message.final is None


def test_server_message_envelope_rejects_missing_required_field() -> None:
    with pytest.raises(ValidationError):
        ServerMessageEnvelope.model_validate(
            {
                "type": "SESSION_STATUS",
                "session_id": str(uuid4()),
                # timestamp intentionally omitted
                "payload": {
                    "state": "ACTIVE",
                    "runtime_substate": None,
                    "interactive": True,
                },
            }
        )


def test_server_message_envelope_rejects_unknown_type() -> None:
    with pytest.raises(ValidationError):
        ServerMessageEnvelope.model_validate(
            {
                "type": "NOT_A_REAL_TYPE",
                "session_id": str(uuid4()),
                "timestamp": datetime.now(UTC).isoformat(),
                "payload": {
                    "state": "ACTIVE",
                    "runtime_substate": None,
                    "interactive": True,
                },
            }
        )


def test_server_message_envelope_json_shape_session_status_stable() -> None:
    session_id = uuid4()
    ts = datetime(2026, 3, 16, 12, 1, 0, tzinfo=UTC)

    message = ServerMessageEnvelope(
        type="SESSION_STATUS",
        session_id=session_id,
        timestamp=ts,
        payload=SessionStatusPayload(
            state="ACTIVE",
            runtime_substate="RUNNING",
            interactive=True,
        ),
        event_index=1,
        final=False,
    )

    payload = message.model_dump(mode="json")

    assert payload["type"] == "SESSION_STATUS"
    assert payload["session_id"] == str(session_id)
    assert payload["timestamp"] == "2026-03-16T12:01:00Z"
    assert payload["payload"] == {
        "state": "ACTIVE",
        "runtime_substate": "RUNNING",
        "interactive": True,
    }
    assert payload["event_index"] == 1
    assert payload["final"] is False
    assert "request_id" in payload
    assert "correlation_id" in payload


def test_server_message_envelope_json_shape_agent_chunk_stable() -> None:
    session_id = uuid4()

    message = ServerMessageEnvelope(
        type="AGENT_TEXT_CHUNK",
        session_id=session_id,
        timestamp=datetime(2026, 3, 16, 12, 2, 0, tzinfo=UTC),
        payload=AgentTextChunkPayload(content="hello", final=True),
        event_index=2,
        request_id=uuid4(),
        correlation_id=uuid4(),
        final=True,
    )

    payload = message.model_dump(mode="json")

    assert payload["type"] == "AGENT_TEXT_CHUNK"
    assert payload["payload"] == {"content": "hello", "final": True}
    assert payload["event_index"] == 2
    assert payload["final"] is True


def test_server_message_envelope_json_shape_policy_denial_stable() -> None:
    message = ServerMessageEnvelope(
        type="POLICY_DENIAL",
        session_id=uuid4(),
        timestamp=datetime(2026, 3, 16, 12, 3, 0, tzinfo=UTC),
        payload=PolicyDenialPayload(
            reason_code="SESSION_NOT_INTERACTIVE",
            message="Session is not interactive.",
        ),
        final=True,
    )

    payload = message.model_dump(mode="json")

    assert payload["type"] == "POLICY_DENIAL"
    assert payload["payload"] == {
        "reason_code": "SESSION_NOT_INTERACTIVE",
        "message": "Session is not interactive.",
    }
    assert payload["final"] is True
