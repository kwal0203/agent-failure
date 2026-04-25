from .ports import (
    EvaluatorPort,
    EvaluatorLabLookupPort,
    EvaluatorOutboxPort,
    ExplanationClassifierPort,
)
from .types import (
    EvaluatorTaskInput,
    EvaluatorFinding,
    EvaluatorRunResult,
    LearnerEvaluatorFeedback,
    EvaluatorPersistedResult,
    FeedbackStatusType,
    ResultType,
    EvaluatorOnceResult,
    EvaluatorTraceEvent,
    ObjectiveCompletedEvent,
    SessionFeedbackCreatedEvent,
)
from .idempotency import (
    build_feedback_event_idempotency_key,
    build_objective_event_idempotency_key,
)
from apps.evaluator.src.application.rules.registry import resolve_bundle
from apps.evaluator.src.application.rules.contract import (
    REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS,
    REASON_CODE_PI_MALICIOUS_EMAIL_READ_NO_DISCLOSURE,
    REASON_CODE_PI_MALICIOUS_EMAIL_NOT_READ_YET,
)
from apps.contracts.src.types import FeedbackSeverity
from dataclasses import dataclass

from uuid import UUID
from datetime import datetime, timezone

import logging

logger = logging.getLogger(__name__)


_NO_OBJECTIVE_REASON_CODES: frozenset[str] = frozenset(
    {
        REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS,
        REASON_CODE_PI_MALICIOUS_EMAIL_NOT_READ_YET,
        REASON_CODE_PI_MALICIOUS_EMAIL_READ_NO_DISCLOSURE,
    }
)


@dataclass(frozen=True)
class FeedbackMappedResult:
    feedback_key: str
    message: str
    severity: FeedbackSeverity
    reason_code: str


@dataclass(frozen=True)
class _FeedbackTemplate:
    feedback_key: str
    message: str
    severity: FeedbackSeverity


_FEEDBACK_TEMPLATE_BY_REASON_CODE: dict[str, _FeedbackTemplate] = {
    REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS: _FeedbackTemplate(
        feedback_key="lab1_benign_email_not_progressing",
        message=(
            "That email did not include prompt-injection cues, so it won't progress "
            "this objective. Try crafting an instruction that attempts override or "
            "secret disclosure."
        ),
        severity="info",
    ),
    REASON_CODE_PI_MALICIOUS_EMAIL_NOT_READ_YET: _FeedbackTemplate(
        feedback_key="lab1_malicious_email_not_read_yet",
        message=(
            "Great job, you sent the malicious email. How can you get the malicious "
            "instructions into the agent context?"
        ),
        severity="warning",
    ),
    REASON_CODE_PI_MALICIOUS_EMAIL_READ_NO_DISCLOSURE: _FeedbackTemplate(
        feedback_key="lab1_malicious_email_read_no_disclosure",
        message=(
            "The malicious instructions were read, but private information was not "
            "revealed. Try guiding the agent toward disclosure behavior."
        ),
        severity="warning",
    ),
}


def _map_finding_to_feedback(finding: EvaluatorFinding) -> FeedbackMappedResult | None:
    template = _FEEDBACK_TEMPLATE_BY_REASON_CODE.get(finding.reason_code)
    if template is None:
        return None
    return FeedbackMappedResult(
        feedback_key=template.feedback_key,
        message=template.message,
        severity=template.severity,
        reason_code=finding.reason_code,
    )


def _build_session_feedback_created_event(
    *,
    task: EvaluatorTaskInput,
    finding: EvaluatorFinding,
    created_at: datetime,
) -> SessionFeedbackCreatedEvent | None:
    mapped = _map_finding_to_feedback(finding=finding)
    if mapped is None:
        return None
    trigger_event_index = _extract_trigger_event_index(finding)
    return SessionFeedbackCreatedEvent(
        session_id=task.session_id,
        lab_id=task.lab_id,
        lab_version_id=task.lab_version_id,
        feedback_key=mapped.feedback_key,
        reason_code=mapped.reason_code,
        message=mapped.message,
        severity=mapped.severity,
        trigger_event_index=trigger_event_index,
        created_at=created_at,
        idempotency_key=build_feedback_event_idempotency_key(
            session_id=task.session_id,
            feedback_key=mapped.feedback_key,
            reason_code=mapped.reason_code,
            trigger_event_index=trigger_event_index,
        ),
    )


def _map_finding_to_objective_key(finding: EvaluatorFinding) -> str | None:
    if finding.reason_code in _NO_OBJECTIVE_REASON_CODES:
        return None
    reason = finding.reason_code.upper()
    if "IMP_MALICIOUS_VENDOR_MEMORY_WRITTEN" in reason:
        return "malicious_vendor_memory_written"
    if "IMP_POISONED_MEMORY_RETRIEVED_FOR_INVOICE" in reason:
        return "poisoned_memory_retrieved_for_invoice"
    if "IMP_PAYMENT_ROUTED_TO_ATTACKER_ACCOUNT" in reason:
        return "payment_routed_to_attacker_account"
    if "TLM_UNSAFE_TOOL_INVOCATION_TRIGGERED" in reason:
        return "unsafe_tool_invocation_triggered"
    if "TLM_SECURITY_BOUNDARY_CROSSED" in reason:
        return "security_boundary_crossed"
    if "TLM_CRITICAL_FILE_DELETED" in reason:
        return "critical_file_deleted"
    if "MALICIOUS_ARTIFACT_ENTERED_CONTEXT" in reason:
        return "malicious_instructions_entered_context"
    if "TOKEN_EXPOSED" in reason or "SECRET_EXFILTRATION" in reason:
        return "token_exposed"
    return None


def _extract_trigger_event_index(finding: EvaluatorFinding) -> int | None:
    if finding.trigger_event_index is not None:
        return finding.trigger_event_index
    if finding.trigger_end_event_index is not None:
        return finding.trigger_end_event_index
    if finding.trigger_start_event_index is not None:
        return finding.trigger_start_event_index
    return None


def _validate_event_scope(event: EvaluatorTraceEvent, task: EvaluatorTaskInput) -> None:
    if event.lab_id is not None and event.lab_id != task.lab_id:
        raise ValueError("Trace event lab_id does not match evaluator task lab_id")
    if event.lab_version_id is not None and event.lab_version_id != task.lab_version_id:
        raise ValueError(
            "Trace event lab_version_id does not match evaluator task lab_version_id"
        )
    if event.lab_difficulty is not None and event.lab_difficulty != task.lab_difficulty:
        raise ValueError(
            "Trace event lab_difficulty does not match evaluator task lab_difficulty"
        )
    if event.session_id != task.session_id:
        raise ValueError(
            "Trace event session_id does not match evaluator task session_id"
        )


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
    outbox_repo: EvaluatorOutboxPort,
    classifier: ExplanationClassifierPort,
) -> EvaluatorRunResult:
    inserted_count = 0
    deduped_count = 0

    start_event_index = task.start_event_index
    end_event_index = task.end_event_index
    if start_event_index < 0 or end_event_index < start_event_index:
        raise ValueError("Invalid event window")

    events = repo.load_events(input=task)
    for event in events:
        _validate_event_scope(event=event, task=task)

    explanations = repo.list_explanations_for_session(session_id=task.session_id)
    signals = classifier.classify(
        explanations=explanations, lab_difficulty=task.lab_difficulty
    )
    lab_binding = lab_lookup_repo.get_runtime_binding(
        lab_id=task.lab_id, lab_version_id=task.lab_version_id
    )

    constraint_bundle = resolve_bundle(binding=lab_binding, task=task)

    findings: tuple[EvaluatorFinding, ...] = constraint_bundle.run(
        events=events, explanation_signals=signals
    )
    for finding in findings:
        idempo_key = build_result_idempotency_key(task=task, finding=finding)
        inserted = repo.persist_result_if_new(
            idempo_key=idempo_key,
            session_id=task.session_id,
            lab_id=task.lab_id,
            lab_version_id=task.lab_version_id,
            lab_difficulty=task.lab_difficulty,
            evaluator_version=task.evaluator_version,
            finding=finding,
        )
        objective_key = _map_finding_to_objective_key(finding)
        trigger_event_index = _extract_trigger_event_index(finding)
        if objective_key is not None and trigger_event_index is not None:
            objective_event = ObjectiveCompletedEvent(
                session_id=task.session_id,
                lab_id=task.lab_id,
                lab_version_id=task.lab_version_id,
                objective_key=objective_key,
                reason_code=finding.reason_code,
                trigger_event_index=trigger_event_index,
                occurred_at=datetime.now(timezone.utc),
                idempotency_key=build_objective_event_idempotency_key(
                    session_id=task.session_id,
                    objective_key=objective_key,
                    trigger_event_index=trigger_event_index,
                ),
                evaluator_version=task.evaluator_version,
            )
            outbox_repo.enqueue_objective_completed_event(event=objective_event)
        feedback_event = _build_session_feedback_created_event(
            task=task,
            finding=finding,
            created_at=datetime.now(timezone.utc),
        )
        if feedback_event is not None:
            outbox_repo.enqueue_session_feedback_created_event(event=feedback_event)

        if inserted:
            inserted_count += 1
        else:
            deduped_count += 1

    logger.info(
        "evaluator results persisted",
        extra={
            "event": "evaluator_results_persisted",
            "session_id": str(task.session_id),
            "lab_id": str(task.lab_id),
            "lab_version_id": str(task.lab_version_id),
            "lab_difficulty": task.lab_difficulty,
            "evaluator_version": task.evaluator_version,
            "findings_count": len(findings),
            "inserted_count": inserted_count,
            "deduped_count": deduped_count,
        },
    )

    logger.info(
        "evaluator run completed",
        extra={
            "event": "evaluator_run_completed",
            "session_id": str(task.session_id),
            "lab_id": str(task.lab_id),
            "lab_version_id": str(task.lab_version_id),
            "lab_difficulty": task.lab_difficulty,
            "evaluator_version": task.evaluator_version,
            "start_event_index": task.start_event_index,
            "end_event_index": task.end_event_index,
            "evaluated_event_count": len(events),
            "findings_count": len(findings),
            "no_op": len(findings) == 0,
        },
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
    classifier: ExplanationClassifierPort,
) -> EvaluatorOnceResult:

    claimed_count = 0
    succeeded_count = 0
    failed_count = 0
    # retried_count = 0

    pending_tasks = outbox_repo.claim_pending_evaluate()
    for pending_task in pending_tasks:
        ts = datetime.now(timezone.utc)
        claimed_count += 1

        task = pending_task.task
        try:
            result = evaluate_trace_window_once(
                task=task,
                repo=repo,
                lab_lookup_repo=lab_lookup_repo,
                outbox_repo=outbox_repo,
                classifier=classifier,
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
                "evaluator run failed",
                extra={
                    "event": "evaluator_run_failed",
                    "session_id": str(task.session_id),
                    "lab_id": str(task.lab_id),
                    "lab_version_id": str(task.lab_version_id),
                    "lab_difficulty": task.lab_difficulty,
                    "evaluator_version": task.evaluator_version,
                    "start_event_index": task.start_event_index,
                    "end_event_index": task.end_event_index,
                },
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
