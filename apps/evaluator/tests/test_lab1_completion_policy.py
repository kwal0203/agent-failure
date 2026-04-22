from datetime import datetime, timezone
from uuid import uuid4

from apps.evaluator.src.application.completion_policy.lab1_success_v1 import (
    LAB1_COMPLETION_POLICY_ID,
    LAB1_COMPLETION_SUCCESS_REASON,
    Lab1SuccessCompletionPolicy,
)
from apps.evaluator.src.application.completion_policy.types import (
    CompletionPolicyInput,
    CompletionPolicyObjectiveRow,
)


def _build_input(
    objectives: tuple[CompletionPolicyObjectiveRow, ...],
) -> CompletionPolicyInput:
    return CompletionPolicyInput(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        objectives=objectives,
    )


def test_lab1_policy_returns_completed_success_when_all_required_objectives_complete() -> (
    None
):
    policy = Lab1SuccessCompletionPolicy()
    evaluated_at = datetime(2026, 4, 22, 12, 0, tzinfo=timezone.utc)

    decision = policy.evaluate(
        input=_build_input(
            (
                CompletionPolicyObjectiveRow(
                    objective_key="malicious_instructions_entered_context",
                    status="complete",
                ),
                CompletionPolicyObjectiveRow(
                    objective_key="unsafe_tool_invocation_triggered",
                    status="complete",
                ),
                CompletionPolicyObjectiveRow(
                    objective_key="token_exposed",
                    status="complete",
                ),
            )
        ),
        evaluated_at=evaluated_at,
    )

    assert decision.completion_status == "completed_success"
    assert decision.completed_at == evaluated_at
    assert decision.completion_reason_code == LAB1_COMPLETION_SUCCESS_REASON
    assert decision.decision_metadata["policy_id"] == LAB1_COMPLETION_POLICY_ID
    assert decision.decision_metadata["required_objective_count"] == 3
    assert decision.decision_metadata["completed_required_objective_count"] == 3
    assert decision.decision_metadata["missing_required_objective_keys"] == ()


def test_lab1_policy_returns_in_progress_when_any_required_objective_pending() -> None:
    policy = Lab1SuccessCompletionPolicy()

    decision = policy.evaluate(
        input=_build_input(
            (
                CompletionPolicyObjectiveRow(
                    objective_key="malicious_instructions_entered_context",
                    status="complete",
                ),
                CompletionPolicyObjectiveRow(
                    objective_key="unsafe_tool_invocation_triggered",
                    status="pending",
                ),
            )
        )
    )

    assert decision.completion_status == "in_progress"
    assert decision.completed_at is None
    assert decision.completion_reason_code is None
    assert decision.decision_metadata["policy_id"] == LAB1_COMPLETION_POLICY_ID
    assert decision.decision_metadata["required_objective_count"] == 2
    assert decision.decision_metadata["completed_required_objective_count"] == 1
    assert decision.decision_metadata["missing_required_objective_keys"] == (
        "unsafe_tool_invocation_triggered",
    )


def test_lab1_policy_ignores_non_required_objectives() -> None:
    policy = Lab1SuccessCompletionPolicy()

    decision = policy.evaluate(
        input=_build_input(
            (
                CompletionPolicyObjectiveRow(
                    objective_key="malicious_instructions_entered_context",
                    status="complete",
                ),
                CompletionPolicyObjectiveRow(
                    objective_key="optional_hint_behavior",
                    status="pending",
                    required=False,
                ),
            )
        )
    )

    assert decision.completion_status == "completed_success"
    assert decision.completion_reason_code == LAB1_COMPLETION_SUCCESS_REASON
    assert decision.decision_metadata["required_objective_count"] == 1
    assert decision.decision_metadata["completed_required_objective_count"] == 1
    assert decision.decision_metadata["missing_required_objective_keys"] == ()
