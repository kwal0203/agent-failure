from .ports import EvaluatorPort
from .types import EvaluatorTaskInput, EvaluatorRunResult  # , EvaluatorOnceResult

import logging

logger = logging.getLogger(__name__)


def evaluate_trace_window_once(
    task: EvaluatorTaskInput, repo: EvaluatorPort
) -> EvaluatorRunResult:
    # claimed_count = 0
    # succeeded_count = 0
    # failed_count = 0
    # # retried_count = 0

    try:
        result = repo.evaluate_trace_window(input=task)
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
