from uuid import UUID

from apps.evaluator.src.application.idempotency import (
    build_feedback_event_idempotency_key,
    build_objective_event_idempotency_key,
    build_result_idempotency_key,
)
from apps.evaluator.src.application.types import EvaluatorFinding, EvaluatorTaskInput


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


def test_build_result_idempotency_key_prefers_single_trigger_event_index() -> None:
    task = EvaluatorTaskInput(
        session_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
        lab_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        lab_version_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
        start_event_index=10,
        end_event_index=20,
    )
    finding = EvaluatorFinding(
        result_type="success_signal",
        code="SIGNAL_1",
        trigger_event_index=14,
        trigger_start_event_index=11,
        trigger_end_event_index=15,
        feedback_level="info",
        reason_code="REASON_1",
        feedback_payload={},
    )

    key = build_result_idempotency_key(
        task=task, rule_bundle_version=7, finding=finding
    )

    assert (
        key == "eval:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa:"
        "cccccccc-cccc-cccc-cccc-cccccccccccc:7:SIGNAL_1:14"
    )


def test_build_result_idempotency_key_falls_back_to_event_range() -> None:
    task = EvaluatorTaskInput(
        session_id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
        lab_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
        lab_version_id=UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"),
        start_event_index=0,
        end_event_index=100,
    )
    finding = EvaluatorFinding(
        result_type="partial_success",
        code="SIGNAL_2",
        trigger_event_index=None,
        trigger_start_event_index=21,
        trigger_end_event_index=27,
        feedback_level="hint",
        reason_code="REASON_2",
        feedback_payload={"x": 1},
    )

    key = build_result_idempotency_key(
        task=task, rule_bundle_version=8, finding=finding
    )

    assert (
        key == "eval:dddddddd-dddd-dddd-dddd-dddddddddddd:"
        "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee:8:SIGNAL_2:21:27"
    )
