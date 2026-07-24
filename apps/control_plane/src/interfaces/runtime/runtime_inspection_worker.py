from apps.control_plane.src.infrastructure.orchestrator.k8s_runtime_inspector import (
    K8sRuntimeInspector,
)
from apps.control_plane.src.application.orchestrator.service import (
    process_reconciliation_once,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemyReconciliationSessionRepository,
)

import logging
from apps.control_plane.src.application.common.observability import (
    log_fields,
)
from apps.control_plane.src.interfaces.runtime.worker_loop import run_worker_loop

logger = logging.getLogger(__name__)
WORKER_NAME = "runtime_inspection_worker"


def run_once() -> None:
    inspector = K8sRuntimeInspector()
    lifecycle_uow = SQLAlchemyUnitOfWork(session_factory=SessionFactory)

    with SessionFactory() as db:
        session_query_repo = SQLAlchemyReconciliationSessionRepository(db=db)
        result = process_reconciliation_once(
            session_query_repo=session_query_repo,
            uow=lifecycle_uow,
            inspector=inspector,
        )
        logger.info(
            "reconciliation worker tick claimed=%s succeeded=%s failed=%s retried=%s",
            result.claimed_count,
            result.succeeded_count,
            result.failed_count,
            result.retried_count,
            extra={**log_fields(), "worker_name": WORKER_NAME},
        )


def run_forever(poll_interval_seconds: float = 1.0) -> None:
    run_worker_loop(
        worker_name=WORKER_NAME,
        run_once=run_once,
        poll_interval_seconds=poll_interval_seconds,
        logger=logger,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
