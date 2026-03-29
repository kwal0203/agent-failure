from .ports import EvaluatorPort, EvaluatorLabLookupPort, EvaluatorOutboxPort
from .types import (
    EvaluatorTaskInput,
    EvaluatorFinding,
    EvaluatorRunResult,
    LearnerEvaluatorFeedback,
    EvaluatorPersistedResult,
    FeedbackStatusType,
    ResultType,
    EvaluatorOnceResult,
)
from apps.evaluator.src.application.rules.registry import resolve_bundle

from uuid import UUID
from datetime import datetime, timezone

import logging

logger = logging.getLogger(__name__)


def build_result_idempotency_key(
    task: EvaluatorTaskInput, finding: EvaluatorFinding
) -> str:
    trigger_ref = (
        str(finding.trigger_event_index)
        if finding.trigger_event_index is not None
        else f"{finding.trigger_start_event_index}:{finding.trigger_end_event_index}"
    )
    return f"eval:{task.session_id}:{task.lab_version_id}:{task.evaluator_version}:{finding.code}:{trigger_ref}"


def evaluate_trace_window_once(
    task: EvaluatorTaskInput,
    repo: EvaluatorPort,
    lab_lookup_repo: EvaluatorLabLookupPort,
) -> EvaluatorRunResult:
    inserted_count = 0
    deduped_count = 0

    start_event_index = task.start_event_index
    end_event_index = task.end_event_index
    if start_event_index < 0 or end_event_index < start_event_index:
        raise ValueError("Invalid event window")

    events = repo.load_events(input=task)
    if any(
        event.lab_id is not None and event.lab_id != task.lab_id for event in events
    ):
        raise ValueError("Trace event lab_id does not match evaluator task lab_id")

    if any(
        event.lab_version_id is not None and event.lab_version_id != task.lab_version_id
        for event in events
    ):
        raise ValueError(
            "Trace event lab_version_id does not match evaluator task lab_version_id"
        )

    if any(event.session_id != task.session_id for event in events):
        raise ValueError(
            "Trace event session_id does not match evaluator task session_id"
        )

    lab_binding = lab_lookup_repo.get_runtime_binding(
        lab_id=task.lab_id, lab_version_id=task.lab_version_id
    )
    constraint_bundle = resolve_bundle(binding=lab_binding, task=task)

    findings: tuple[EvaluatorFinding, ...] = constraint_bundle.run(events=events)
    for finding in findings:
        idempo_key = build_result_idempotency_key(task=task, finding=finding)
        inserted = repo.persist_result_if_new(
            idempo_key=idempo_key,
            session_id=task.session_id,
            lab_id=task.lab_id,
            lab_version_id=task.lab_version_id,
            evaluator_version=task.evaluator_version,
            finding=finding,
        )

        if inserted:
            inserted_count += 1
        else:
            deduped_count += 1

    logger.info(
        "evaluator.results.persisted session_id=%s lab_id=%s lab_version_id=%s evaluator_version=%s findings_count=%s inserted_count=%s deduped_count=%s",
        task.session_id,
        task.lab_id,
        task.lab_version_id,
        task.evaluator_version,
        len(findings),
        inserted_count,
        deduped_count,
    )
    logger.info(
        "evaluator.run.completed session_id=%s lab_id=%s lab_version_id=%s evaluator_version=%s start_event_index=%s end_event_index=%s evaluated_event_count=%s findings_count=%s no_op=%s",
        task.session_id,
        task.lab_id,
        task.lab_version_id,
        task.evaluator_version,
        task.start_event_index,
        task.end_event_index,
        len(events),
        len(findings),
        len(findings) == 0,
    )

    return EvaluatorRunResult(
        session_id=task.session_id,
        lab_id=task.lab_id,
        lab_version_id=task.lab_version_id,
        evaluator_version=task.evaluator_version,
        start_event_index=task.start_event_index,
        end_event_index=task.end_event_index,
        evaluated_event_count=len(events),
        findings_count=len(findings),
        no_op=len(findings) == 0,
        findings=findings,
        inserted_count=inserted_count,
        deduped_count=deduped_count,
    )


def process_evaluate_pending_once(
    repo: EvaluatorPort,
    lab_lookup_repo: EvaluatorLabLookupPort,
    outbox_repo: EvaluatorOutboxPort,
) -> EvaluatorOnceResult:

    claimed_count = 0
    succeeded_count = 0
    failed_count = 0
    # retried_count = 0

    pending_tasks = outbox_repo.claim_pending_evaluate()
    for pending_task in pending_tasks:
        claimed_count += 1
        task = pending_task.task
        ts = datetime.now(timezone.utc)
        try:
            result = evaluate_trace_window_once(
                task=task,
                repo=repo,
                lab_lookup_repo=lab_lookup_repo,
            )

            if result.inserted_count > 0:
                outbox_repo.enqueue_learner_feedback_publish_request(
                    session_id=task.session_id, requested_at=ts
                )
            outbox_repo.mark_processed(outbox_event_id=pending_task.outbox_event_id)
            succeeded_count += 1
        except Exception as exc:
            outbox_repo.mark_terminal_failure(
                outbox_event_id=pending_task.outbox_event_id, error_message=str(exc)
            )
            failed_count += 1

            logger.exception(
                "evaluator.run.failed session_id=%s lab_id=%s lab_version_id=%s evaluator_version=%s start_event_index=%s end_event_index=%s",
                task.session_id,
                task.lab_id,
                task.lab_version_id,
                task.evaluator_version,
                task.start_event_index,
                task.end_event_index,
            )

    return EvaluatorOnceResult(
        claimed_count=claimed_count,
        succeeded_count=succeeded_count,
        failed_count=failed_count,
        retried_count=0,
    )


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


def get_learner_feedback(
    session_id: UUID, repo: EvaluatorPort
) -> tuple[LearnerEvaluatorFeedback, ...]:
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
