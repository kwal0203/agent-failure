from uuid import UUID
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.common.errors import ForbiddenError

from .types import (
    LearnerEvaluatorFeedback,
    ResultType,
    FeedbackStatusType,
    EvaluatorPersistedResult,
)
from .ports import EvaluatorPort


def _build_evidence_snippet(result: EvaluatorPersistedResult) -> str:
    p = result.feedback_payload

    if result.code == "pi.secret_exfiltration_success":
        v = p.get("matched_value")
        return v if isinstance(v, str) else "Secret-like output detected"

    if result.code == "pi.protected_tool_access_violation":
        tool = p.get("tool_name")
        target = p.get("target_resource")
        if isinstance(tool, str) and isinstance(target, str):
            return f"{tool} accessed protected resource {target}."
        return "Protected resource tool access detected."

    if result.code == "pi.attack_attempt_blocked":
        blocked_by = p.get("blocked_by")
        reason = p.get("block_reason_code")
        if isinstance(blocked_by, str) and isinstance(reason, str):
            return f"Attack attempt blocked by {blocked_by} ({reason})"
        return "Attack attempt was blocked."

    return result.reason_code


def get_session_evaluator_feedback(
    principal: PrincipalContext,
    session_id: UUID,
    repo: EvaluatorPort,
) -> tuple[LearnerEvaluatorFeedback, ...]:
    if principal.role not in {"learner", "admin"}:
        raise ForbiddenError(role=principal.role)

    mapping: dict[ResultType, FeedbackStatusType] = {
        "constraint_violation": "learned",
        "success_signal": "learned",
        "partial_success": "progress",
        "no_effect": "no_progress",
        "terminal_outcome": "session_terminal",
    }

    persisted_results = repo.list_results_for_session(session_id=session_id)
    learner_feedback: list[LearnerEvaluatorFeedback] = []
    for result in persisted_results:
        try:
            status = mapping[result.result_type]
        except KeyError as exc:
            raise ValueError(f"Unsupported result_type: {result.result_type}") from exc

        learner_feedback.append(
            LearnerEvaluatorFeedback(
                status=status,
                reason_code=result.reason_code,
                evidence_snippet=_build_evidence_snippet(result=result),
            )
        )

    return tuple(learner_feedback)
