from apps.control_plane.src.infrastructure.persistence.unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemyExpirySessionRepository,
)
from apps.control_plane.src.application.orchestrator.service import process_expiry_once

import time
import logging

logger = logging.getLogger(__name__)


def run_once() -> None:
    uow = SQLAlchemyUnitOfWork(session_factory=SessionFactory)
    with SessionFactory() as db:
        session_query_repo = SQLAlchemyExpirySessionRepository(db=db)
        result = process_expiry_once(session_query_repo=session_query_repo, uow=uow)
        logger.info(
            "expiry worker tick claimed=%s succeeded=%s failed=%s retried=%s",
            result.claimed_count,
            result.succeeded_count,
            result.failed_count,
            result.retried_count,
        )


def run_forever(polling_interval_seconds: float = 1.0) -> None:
    # TODO(P0-E1 follow-up): harden worker loop with try/except around run_once
    # so unexpected per-tick exceptions are logged and do not kill the process.
    while True:
        run_once()
        time.sleep(polling_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
