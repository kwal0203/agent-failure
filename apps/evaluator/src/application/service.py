from .ports import EvaluatorPort
from .types import (
    EvaluatorTaskInput,
    EvaluatorRunResult,
    EvaluatorFinding,
)  # , EvaluatorOnceResult

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
    task: EvaluatorTaskInput, repo: EvaluatorPort
) -> EvaluatorRunResult:

    inserted_count = 0
    deduped_count = 0

    try:
        result = repo.evaluate_trace_window(input=task)
        findings = result.findings
        for finding in findings:
            idempo_key = build_result_idempotency_key(task=task, finding=finding)
            inserted = repo.persist_result_if_new(
                idempo_key=idempo_key,
                session_id=result.session_id,
                lab_id=result.lab_id,
                lab_version_id=result.lab_version_id,
                evaluator_version=result.evaluator_version,
                finding=finding,
            )
            if inserted:
                inserted_count += 1
            else:
                deduped_count += 1

        logger.info(
            "evaluator.results.persisted session_id=%s lab_id=%s lab_version_id=%s evaluator_version=%s findings_count=%s inserted_count=%s deduped_count=%s",
            result.session_id,
            result.lab_id,
            result.lab_version_id,
            result.evaluator_version,
            result.findings_count,
            inserted_count,
            deduped_count,
        )

        logger.info(
            "evaluator.run.completed session_id=%s lab_id=%s lab_version_id=%s evaluator_version=%s start_event_index=%s end_event_index=%s evaluated_event_count=%s findings_count=%s no_op=%s",
            result.session_id,
            result.lab_id,
            result.lab_version_id,
            result.evaluator_version,
            result.start_event_index,
            result.end_event_index,
            result.evaluated_event_count,
            result.findings_count,
            result.no_op,
        )
        return result
    except Exception:
        logger.exception(
            "evaluator.run.failed session_id=%s lab_id=%s lab_version_id=%s evaluator_version=%s start_event_index=%s end_event_index=%s",
            task.session_id,
            task.lab_id,
            task.lab_version_id,
            task.evaluator_version,
            task.start_event_index,
            task.end_event_index,
        )
        raise
