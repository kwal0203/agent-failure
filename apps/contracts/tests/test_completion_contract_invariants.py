from typing import get_args

from pydantic import BaseModel

from apps.contracts.src.schemas import (
    OutboxEvent,
    OutboxEventType,
    SessionCompletedEventPayload,
    SessionCompletedOutboxEvent,
    SessionFeedbackCreatedOutboxEvent,
)
from apps.contracts.src.types import (
    OutboxEventName,
    SessionCompletedEventName,
    SessionFeedbackCreatedEventName,
)


def _outbox_union_members() -> tuple[type[BaseModel], ...]:
    annotated_args = get_args(OutboxEvent)
    member_or_union = annotated_args[0]
    union_members = get_args(member_or_union)
    if union_members:
        return union_members
    return (member_or_union,)


def _event_type_literal_values() -> tuple[str, ...]:
    return get_args(OutboxEventName)


def test_completion_event_literals_are_single_source() -> None:
    assert get_args(SessionCompletedEventName) == ("session.completed.v1",)
    assert get_args(SessionFeedbackCreatedEventName) == ("session.feedback.created.v1",)
    assert get_args(OutboxEventName) == (
        "session.completed.v1",
        "session.feedback.created.v1",
    )
    assert get_args(OutboxEventType) == get_args(OutboxEventName)


def test_outbox_event_union_registration_matches_event_literals_order() -> None:
    members = _outbox_union_members()
    assert members == (SessionCompletedOutboxEvent, SessionFeedbackCreatedOutboxEvent)

    discriminator_values = tuple(
        member.model_fields["event_type"].default for member in members
    )
    assert discriminator_values == _event_type_literal_values()


def test_session_completed_payload_keys_match_contract_exactly() -> None:
    assert tuple(SessionCompletedEventPayload.model_fields.keys()) == (
        "session_id",
        "lab_id",
        "lab_version_id",
        "outcome",
        "completion_reason_code",
        "trigger_event_index",
        "occurred_at",
        "idempotency_key",
    )


def test_session_completed_nullable_contract_fields_are_explicit() -> None:
    fields = SessionCompletedEventPayload.model_fields
    assert not fields["completion_reason_code"].is_required()
    assert not fields["trigger_event_index"].is_required()
    assert fields["session_id"].is_required()
    assert fields["lab_id"].is_required()
    assert fields["lab_version_id"].is_required()
    assert fields["outcome"].is_required()
    assert fields["occurred_at"].is_required()
    assert fields["idempotency_key"].is_required()
