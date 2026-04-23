from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import TypeAdapter, ValidationError

from apps.contracts.src.idempotency import (
    build_session_completed_event_idempotency_key,
)
from apps.contracts.src.schemas import OutboxEvent, SessionCompletedEventPayload


def _valid_payload(*, idempotency_key: str) -> dict[str, object]:
    return {
        "session_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "lab_id": "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "lab_version_id": "cccccccc-cccc-cccc-cccc-cccccccccccc",
        "outcome": "completed_success",
        "completion_reason_code": "LAB_OBJECTIVES_COMPLETE",
        "trigger_event_index": 21,
        "occurred_at": datetime(2026, 4, 22, 12, 0, 0, tzinfo=timezone.utc),
        "idempotency_key": idempotency_key,
    }


def test_session_completed_payload_valid_passes() -> None:
    payload = SessionCompletedEventPayload.model_validate(
        _valid_payload(idempotency_key="session_completed:test")
    )
    assert payload.outcome == "completed_success"
    assert payload.trigger_event_index == 21
    assert payload.completion_reason_code == "LAB_OBJECTIVES_COMPLETE"


def test_session_completed_outbox_event_union_validates() -> None:
    adapter: TypeAdapter[OutboxEvent] = TypeAdapter(OutboxEvent)
    parsed = adapter.validate_python(
        {
            "event_type": "session.completed.v1",
            "aggregate_id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "payload": _valid_payload(idempotency_key="session_completed:test"),
        }
    )
    assert parsed.event_type == "session.completed.v1"
    assert parsed.aggregate_id == UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    assert parsed.payload.idempotency_key == "session_completed:test"


def test_session_completed_payload_missing_required_field_fails() -> None:
    raw = _valid_payload(idempotency_key="session_completed:test")
    raw.pop("lab_id")

    with pytest.raises(ValidationError) as exc:
        SessionCompletedEventPayload.model_validate(raw)

    assert "lab_id" in str(exc.value)


def test_session_completed_payload_invalid_outcome_fails() -> None:
    raw = _valid_payload(idempotency_key="session_completed:test")
    raw["outcome"] = "done"

    with pytest.raises(ValidationError) as exc:
        SessionCompletedEventPayload.model_validate(raw)

    assert "outcome" in str(exc.value)


def test_session_completed_payload_wrong_types_fail() -> None:
    raw = _valid_payload(idempotency_key="session_completed:test")
    raw["session_id"] = "not-a-uuid"
    raw["trigger_event_index"] = "twenty-one"

    with pytest.raises(ValidationError) as exc:
        SessionCompletedEventPayload.model_validate(raw)

    message = str(exc.value)
    assert "session_id" in message
    assert "trigger_event_index" in message


def test_session_completed_idempotency_replay_safety_same_semantics_same_key() -> None:
    session_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    key_a = build_session_completed_event_idempotency_key(
        session_id=session_id,
        outcome="completed_success",
        completion_reason_code="  LAB_OBJECTIVES_COMPLETE ",
        trigger_event_index=21,
    )
    key_b = build_session_completed_event_idempotency_key(
        session_id=session_id,
        outcome="completed_success",
        completion_reason_code="lab_objectives_complete",
        trigger_event_index=21,
    )

    assert key_a == key_b
