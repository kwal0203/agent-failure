from uuid import UUID

from apps.contracts.src.idempotency import (
    build_session_completed_event_idempotency_key,
)


def test_build_session_completed_event_idempotency_key_is_stable() -> None:
    session_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")

    key_a = build_session_completed_event_idempotency_key(
        session_id=session_id,
        outcome="completed_success",
        completion_reason_code="LAB_OBJECTIVES_COMPLETE",
        trigger_event_index=42,
    )
    key_b = build_session_completed_event_idempotency_key(
        session_id=session_id,
        outcome="completed_success",
        completion_reason_code="LAB_OBJECTIVES_COMPLETE",
        trigger_event_index=42,
    )

    assert key_a == key_b
    assert (
        key_a == "session_completed:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa:"
        "completed_success:lab_objectives_complete:42"
    )


def test_build_session_completed_event_idempotency_key_normalizes_inputs() -> None:
    session_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    key = build_session_completed_event_idempotency_key(
        session_id=session_id,
        outcome="completed_failure",
        completion_reason_code="  RUNTIME_ERROR  ",
        trigger_event_index=None,
    )

    assert (
        key == "session_completed:bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb:"
        "completed_failure:runtime_error:none"
    )


def test_build_session_completed_event_idempotency_key_uses_none_for_empty_reason() -> (
    None
):
    session_id = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")

    key = build_session_completed_event_idempotency_key(
        session_id=session_id,
        outcome="completed_failure",
        completion_reason_code="   ",
        trigger_event_index=0,
    )

    assert (
        key == "session_completed:cccccccc-cccc-cccc-cccc-cccccccccccc:"
        "completed_failure:none:0"
    )
