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

import time

import logging
from apps.control_plane.src.application.common.observability import (
    log_fields,
    reset_correlation_id,
    set_correlation_id,
)

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
    # TODO(P0-E1 follow-up): harden worker loop with try/except around run_once
    # so unexpected per-tick exceptions are logged and do not kill the process.
    while True:
        token = set_correlation_id(None)
        try:
            run_once()
        finally:
            reset_correlation_id(token)
        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
