from uuid import UUID

from apps.evaluator.src.application.idempotency import (
    build_feedback_event_idempotency_key,
    build_objective_event_idempotency_key,
)


def test_build_objective_event_idempotency_key_normalizes_objective_key() -> None:
    key = build_objective_event_idempotency_key(
        session_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        objective_key="  Token_Exposed  ",
        trigger_event_index=12,
    )

    assert key == "objective:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa:token_exposed:12"


def test_build_feedback_event_idempotency_key_is_deterministic_and_normalized() -> None:
    key = build_feedback_event_idempotency_key(
        session_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        feedback_key="  Lab1_Benign_Email_Not_Progressing  ",
        reason_code="  PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS ",
        trigger_event_index=8,
    )

    assert (
        key == "feedback:v1:bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb:"
        "lab1_benign_email_not_progressing:pi_benign_email_injected_no_progress:8"
    )


def test_build_feedback_event_idempotency_key_uses_none_sentinel_when_trigger_missing() -> (
    None
):
    key = build_feedback_event_idempotency_key(
        session_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        feedback_key="lab1_benign_email_not_progressing",
        reason_code="PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS",
        trigger_event_index=None,
    )

    assert (
        key == "feedback:v1:cccccccc-cccc-cccc-cccc-cccccccccccc:"
        "lab1_benign_email_not_progressing:pi_benign_email_injected_no_progress:none"
    )
