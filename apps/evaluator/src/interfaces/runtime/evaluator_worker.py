from apps.evaluator.src.infrastructure.evaluator_repository import (
    SQLAlchemyEvaluatorRepository,
)
from apps.evaluator.src.infrastructure.lab_lookup_repository import (
    SQLAlchemyEvaluatorLabLookupRepository,
)
from apps.evaluator.src.application.service import evaluate_trace_window_once
from apps.evaluator.src.application.types import EvaluatorTaskInput, EvaluatorRunResult
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from collections.abc import Sequence

import logging

logger = logging.getLogger(__name__)


def run_once(task: EvaluatorTaskInput) -> EvaluatorRunResult:
    logger.info(
        "evaluator.worker.run_once.start session_id=%s lab_id=%s lab_version_id=%s evaluator_version=%s start_event_index=%s end_event_index=%s",
        task.session_id,
        task.lab_id,
        task.lab_version_id,
        task.evaluator_version,
        task.start_event_index,
        task.end_event_index,
    )

    with SessionFactory() as db:
        try:
            evaluator_repo = SQLAlchemyEvaluatorRepository(db=db)
            lab_lookup_repo = SQLAlchemyEvaluatorLabLookupRepository(db=db)
            result = evaluate_trace_window_once(
                task=task, repo=evaluator_repo, lab_lookup_repo=lab_lookup_repo
            )
            db.commit()
            logger.info(
                "evaluator.worker.run_once.done session_id=%s lab_id=%s lab_version_id=%s evaluator_version=%s start_event_index=%s end_event_index=%s evaluated_event_count=%s findings_count=%s no_op=%s",
                task.session_id,
                task.lab_id,
                task.lab_version_id,
                task.evaluator_version,
                task.start_event_index,
                task.end_event_index,
                result.evaluated_event_count,
                result.findings_count,
                result.no_op,
            )
            return result
        except Exception:
            db.rollback()
            logger.exception(
                "evaluator.worker.run_once.failed session_id=%s lab_id=%s lab_version_id=%s evaluator_version=%s start_event_index=%s end_event_index=%s",
                task.session_id,
                task.lab_id,
                task.lab_version_id,
                task.evaluator_version,
                task.start_event_index,
                task.end_event_index,
            )
            raise


# def run_forever(task: EvaluatorTaskInput, poll_interval_seconds: float = 10.0) -> None:
#     while True:
#         run_once(task=task)
#         time.sleep(poll_interval_seconds)


def run_batch(tasks: Sequence[EvaluatorTaskInput]) -> list[EvaluatorRunResult]:
    """Run a caller-provided batch of evaluation tasks.

    TODO(P1-E7-T3): Replace this temporary task-driven path with queue/outbox
    claim-and-process semantics so run_once() can execute one claimed worker tick.
    """
    results: list[EvaluatorRunResult] = []
    for task in tasks:
        results.append(run_once(task=task))

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("evaluator worker module loaded; queue mode not wired yet")
