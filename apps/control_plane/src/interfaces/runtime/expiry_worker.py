from apps.control_plane.src.infrastructure.persistence.unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemyExpirySessionRepository,
)
from apps.control_plane.src.application.orchestrator.service import process_expiry_once
from apps.control_plane.src.application.orchestrator.policy import ExpiryPolicy
from apps.control_plane.src.infrastructure.config.settings import (
    get_orchestrator_settings,
)

import logging
from apps.control_plane.src.application.common.observability import (
    log_fields,
)
from apps.control_plane.src.interfaces.runtime.worker_loop import run_worker_loop

logger = logging.getLogger(__name__)
WORKER_NAME = "expiry_worker"


def run_once() -> None:
    uow = SQLAlchemyUnitOfWork(session_factory=SessionFactory)
    settings = get_orchestrator_settings()
    with SessionFactory() as db:
        session_query_repo = SQLAlchemyExpirySessionRepository(db=db)
        result = process_expiry_once(
            session_query_repo=session_query_repo,
            uow=uow,
            policy=ExpiryPolicy(
                provisioning_timeout_seconds=settings.provisioning_timeout_seconds,
                max_session_lifetime_seconds=(settings.max_session_lifetime_seconds),
            ),
        )
        logger.info(
            "expiry worker tick claimed=%s succeeded=%s failed=%s retried=%s",
            result.claimed_count,
            result.succeeded_count,
            result.failed_count,
            result.retried_count,
            extra={**log_fields(), "worker_name": WORKER_NAME},
        )


def run_forever(polling_interval_seconds: float = 1.0) -> None:
    run_worker_loop(
        worker_name=WORKER_NAME,
        run_once=run_once,
        poll_interval_seconds=polling_interval_seconds,
        logger=logger,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
