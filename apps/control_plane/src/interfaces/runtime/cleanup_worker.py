from apps.control_plane.src.application.orchestrator.service import (
    process_cleanup_pending_once,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work_cleanup_session import (
    SQLAlchemyUnitOfWorkCleanupSession,
)
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.orchestrator.k8s_teardown import (
    K8sRuntimeTeardown,
)

import time
import logging

logger = logging.getLogger(__name__)


def _build_dependencies() -> tuple[
    SQLAlchemyUnitOfWorkCleanupSession, K8sRuntimeTeardown
]:
    uow = SQLAlchemyUnitOfWorkCleanupSession(session_factory=SessionFactory)
    teardown = K8sRuntimeTeardown()
    return uow, teardown


def run_once() -> None:
    uow, teardown = _build_dependencies()
    result = process_cleanup_pending_once(uow=uow, teardown=teardown)
    logger.info(
        "cleanup worker tick claimed=%s succeeded=%s failed=%s retried=%s",
        result.claimed_count,
        result.succeeded_count,
        result.failed_count,
        result.retried_count,
    )


def run_forever(poll_interval_seconds: float = 1.0) -> None:
    while True:
        run_once()
        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
