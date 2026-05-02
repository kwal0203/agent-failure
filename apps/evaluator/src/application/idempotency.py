from apps.evaluator.src.application.types import EvaluatorFinding, EvaluatorTaskInput
from uuid import UUID


def build_objective_event_idempotency_key(
    *,
    session_id: UUID,
    objective_key: str,
    trigger_event_index: int,
) -> str:
    normalized_objective_key = objective_key.strip().lower()
    return f"objective:{session_id}:{normalized_objective_key}:{trigger_event_index}"


def build_feedback_event_idempotency_key(
    *,
    session_id: UUID,
    feedback_key: str,
    reason_code: str,
    trigger_event_index: int | None,
) -> str:
    normalized_feedback_key = feedback_key.strip().lower()
    normalized_reason_code = reason_code.strip().lower()
    normalized_trigger = (
        str(trigger_event_index) if trigger_event_index is not None else "none"
    )
    # v1 format must remain stable for replay-safe dedupe across evaluator passes.
    return (
        f"feedback:v1:{session_id}:{normalized_feedback_key}:"
        f"{normalized_reason_code}:{normalized_trigger}"
    )


def build_result_idempotency_key(
    *, task: EvaluatorTaskInput, finding: EvaluatorFinding
) -> str:
    trigger_ref = (
        str(finding.trigger_event_index)
        if finding.trigger_event_index is not None
        else f"{finding.trigger_start_event_index}:{finding.trigger_end_event_index}"
    )
    return (
        f"eval:{task.session_id}:{task.lab_version_id}:{task.evaluator_version}:"
        f"{finding.code}:{trigger_ref}"
    )
