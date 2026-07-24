from apps.evaluator.src.infrastructure.evaluator_repository import (
    SQLAlchemyEvaluatorRepository,
)
from apps.evaluator.src.infrastructure.lab_lookup_repository import (
    SQLAlchemyEvaluatorLabLookupRepository,
)
from apps.evaluator.src.application.service import process_evaluate_pending_once
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.evaluator.src.infrastructure.outbox_evaluator_repository import (
    SQLAlchemyOutboxEvaluatorRepository,
)
from apps.evaluator.src.infrastructure.explanation_classifier import (
    ExplanationClassifierRepository,
)
from apps.evaluator.src.application.ports import ExplanationClassifierPort

from .config import load_evaluator_runtime_config

import time
import logging

from apps.control_plane.src.application.common.observability import (
    log_fields,
    reset_correlation_id,
    set_correlation_id,
)

logger = logging.getLogger(__name__)
WORKER_NAME = "evaluator_worker"


def _build_classifier() -> ExplanationClassifierRepository:
    classifier_config = load_evaluator_runtime_config()
    return ExplanationClassifierRepository(
        base_url=classifier_config.provider_endpoint,
        api_key=classifier_config.openrouter_api_key,
        model=classifier_config.model_name,
        timeout_seconds=classifier_config.model_timeout,
    )


def run_once(*, classifier_repo: ExplanationClassifierPort) -> None:
    with SessionFactory() as db:
        evaluator_repo = SQLAlchemyEvaluatorRepository(db=db)
        lab_lookup_repo = SQLAlchemyEvaluatorLabLookupRepository(db=db)
        outbox_repo = SQLAlchemyOutboxEvaluatorRepository(db=db)

        try:
            result = process_evaluate_pending_once(
                repo=evaluator_repo,
                lab_lookup_repo=lab_lookup_repo,
                outbox_repo=outbox_repo,
                classifier=classifier_repo,
            )
            db.commit()
            logger.info(
                "evaluator worker tick completed",
                extra={
                    "event": "evaluator_worker_tick_completed",
                    "claimed_count": result.claimed_count,
                    "succeeded_count": result.succeeded_count,
                    "failed_count": result.failed_count,
                    "retried_count": result.retried_count,
                },
            )
        except Exception:
            db.rollback()
            raise


def run_forever(poll_interval_seconds: float = 1.0) -> None:
    classifier_repo = _build_classifier()
    while True:
        token = set_correlation_id(None)
        try:
            run_once(classifier_repo=classifier_repo)
        except Exception:
            logger.exception(
                "evaluator worker tick failed",
                extra={
                    **log_fields(),
                    "event": "evaluator_worker_tick_failed",
                    "worker_name": WORKER_NAME,
                },
            )
        finally:
            reset_correlation_id(token)
        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever(poll_interval_seconds=10.0)
