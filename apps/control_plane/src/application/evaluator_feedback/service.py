from uuid import UUID
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.common.errors import ForbiddenError

from .types import (
    LearnerEvaluatorFeedback,
    ResultType,
    FeedbackStatusType,
    EvaluatorPersistedResult,
    LearnerFeedbackPublishResult,
)
from .ports import (
    EvaluatorPort,
    OutboxLearnerFeedbackPublishPort,
    LearnerFeedbackPublisherPort,
)

import logging

logger = logging.getLogger(__name__)


MAPPING: dict[ResultType, FeedbackStatusType] = {
    "constraint_violation": "learned",
    "success_signal": "learned",
    "partial_success": "progress",
    "no_effect": "no_progress",
    "terminal_outcome": "session_terminal",
}


def _project_feedback_for_session(
    session_id: UUID, eval_repo: EvaluatorPort
) -> tuple[LearnerEvaluatorFeedback, ...]:
    learner_feedback: list[LearnerEvaluatorFeedback] = []
    persisted_results = eval_repo.list_results_for_session(session_id=session_id)
    for result in persisted_results:
        try:
            status = MAPPING[result.result_type]
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

    return _project_feedback_for_session(session_id=session_id, eval_repo=repo)


async def process_pending_feedback_publish_once(
    *,
    outbox_repo: OutboxLearnerFeedbackPublishPort,
    eval_repo: EvaluatorPort,
    publisher: LearnerFeedbackPublisherPort,
) -> LearnerFeedbackPublishResult:

    claimed_count = 0
    succeeded_count = 0
    failed_count = 0
    retried_count = 0

    events = outbox_repo.claim_pending_feedback_publish()
    logger.info(
        "learner_feedback.publish.batch_started claimed_count=%s",
        len(events),
    )

    for event in events:
        claimed_count += 1
        try:
            learner_feedback = _project_feedback_for_session(
                session_id=event.session_id, eval_repo=eval_repo
            )
            await publisher.publish_session_feedback(
                session_id=event.session_id, feedback=learner_feedback
            )
            outbox_repo.mark_processed(outbox_event_id=event.outbox_event_id)
            succeeded_count += 1
            logger.info(
                "learner_feedback.publish.succeeded outbox_event_id=%s session_id=%s feedback_count=%s",
                event.outbox_event_id,
                event.session_id,
                len(learner_feedback),
            )
        except ValueError as exc:
            outbox_repo.mark_terminal_failure(
                outbox_event_id=event.outbox_event_id, error_message=str(exc)
            )
            failed_count += 1
            logger.info(
                "learner_feedback.publish.terminal_failure outbox_event_id=%s session_id=%s error=%s",
                event.outbox_event_id,
                event.session_id,
                str(exc),
            )
        except Exception as exc:
            logger.exception(
                "feedback publish failed session_id=%s, outbox_event_id=%s",
                event.session_id,
                event.outbox_event_id,
            )
            outbox_repo.mark_retryable_failure(
                outbox_event_id=event.outbox_event_id, error_message=str(exc)
            )
            retried_count += 1
            logger.info(
                "learner_feedback.publish.retryable_failure outbox_event_id=%s session_id=%s error=%s",
                event.outbox_event_id,
                event.session_id,
                str(exc),
            )

    result = LearnerFeedbackPublishResult(
        claimed_count=claimed_count,
        succeeded_count=succeeded_count,
        failed_count=failed_count,
        retried_count=retried_count,
    )

    return result
