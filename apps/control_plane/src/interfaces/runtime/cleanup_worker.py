from apps.control_plane.src.application.orchestrator.service import (
    process_cleanup_pending_once,
)
from apps.control_plane.src.application.orchestrator.policy import CleanupPolicy
from apps.control_plane.src.infrastructure.config.settings import (
    get_orchestrator_settings,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work_cleanup_session import (
    SQLAlchemyUnitOfWorkCleanupSession,
)
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.orchestrator.k8s_teardown import (
    K8sRuntimeTeardown,
)

import logging
from apps.control_plane.src.application.common.observability import (
    log_fields,
)
from apps.control_plane.src.interfaces.runtime.worker_loop import run_worker_loop

logger = logging.getLogger(__name__)
WORKER_NAME = "cleanup_worker"


def _build_dependencies() -> tuple[
    SQLAlchemyUnitOfWorkCleanupSession, K8sRuntimeTeardown
]:
    uow = SQLAlchemyUnitOfWorkCleanupSession(session_factory=SessionFactory)
    teardown = K8sRuntimeTeardown()
    return uow, teardown


def run_once() -> None:
    uow, teardown = _build_dependencies()
    settings = get_orchestrator_settings()
    result = process_cleanup_pending_once(
        uow=uow,
        teardown=teardown,
        policy=CleanupPolicy(
            max_attempts=settings.cleanup_max_attempts,
            retry_backoff_seconds=settings.cleanup_retry_backoff_seconds,
            already_gone_reverify_backoff_seconds=(
                settings.cleanup_reverify_backoff_seconds
            ),
        ),
    )
    logger.info(
        "cleanup worker tick claimed=%s succeeded=%s failed=%s retried=%s",
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
    run_forever(poll_interval_seconds=10.0)
