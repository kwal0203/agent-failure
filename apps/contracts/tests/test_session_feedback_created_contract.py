from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import TypeAdapter, ValidationError

from apps.contracts.src.schemas import (
    OutboxEvent,
    SessionFeedbackCreatedEventPayload,
    SessionFeedbackCreatedOutboxEvent,
)


def _valid_payload(*, idempotency_key: str) -> dict[str, object]:
    return {
        "session_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "lab_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "lab_version_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "feedback_key": "lab1_benign_email_not_progressing",
        "reason_code": "FBK_BENIGN_EMAIL_NOT_PROGRESSING",
        "message": "This action did not progress the objective.",
        "severity": "info",
        "trigger_event_index": None,
        "created_at": datetime(2026, 4, 23, 12, 0, 0, tzinfo=timezone.utc),
        "idempotency_key": idempotency_key,
    }


def test_session_feedback_created_payload_valid_passes() -> None:
    payload = SessionFeedbackCreatedEventPayload.model_validate(
        _valid_payload(idempotency_key="session_feedback:test")
    )
    assert payload.feedback_key == "lab1_benign_email_not_progressing"
    assert payload.trigger_event_index is None
    assert payload.severity == "info"


def test_session_feedback_created_outbox_event_union_validates() -> None:
    adapter: TypeAdapter[OutboxEvent] = TypeAdapter(OutboxEvent)
    parsed = adapter.validate_python(
        {
            "event_type": "session.feedback.created.v1",
            "aggregate_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "payload": _valid_payload(idempotency_key="session_feedback:test"),
        }
    )
    assert parsed.event_type == "session.feedback.created.v1"
    assert parsed.aggregate_id == UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    assert parsed.payload.idempotency_key == "session_feedback:test"
    assert parsed.payload.trigger_event_index is None


def test_session_feedback_created_nullable_fields_preserved_on_serialization() -> None:
    event = SessionFeedbackCreatedOutboxEvent.model_validate(
        {
            "event_type": "session.feedback.created.v1",
            "aggregate_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "payload": _valid_payload(idempotency_key="session_feedback:test"),
        }
    )
    dumped = event.payload.model_dump(mode="json", exclude_none=False)
    assert "trigger_event_index" in dumped
    assert dumped["trigger_event_index"] is None


def test_session_feedback_created_payload_invalid_severity_fails() -> None:
    raw = _valid_payload(idempotency_key="session_feedback:test")
    raw["severity"] = "critical"

    with pytest.raises(ValidationError) as exc:
        SessionFeedbackCreatedEventPayload.model_validate(raw)

    assert "severity" in str(exc.value)
