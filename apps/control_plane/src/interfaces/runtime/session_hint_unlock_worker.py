import logging
from apps.control_plane.src.application.common.observability import (
    log_fields,
)
from apps.control_plane.src.interfaces.runtime.worker_loop import run_worker_loop

from apps.control_plane.src.application.session_hints.service import (
    process_due_session_hints_once,
)
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.outbox import SQLAlchemyOutbox
from apps.control_plane.src.infrastructure.persistence.session_hints_repository import (
    SQLAlchemySessionHintProjectorRepository,
)

logger = logging.getLogger(__name__)
WORKER_NAME = "session_hint_unlock_worker"


def run_once() -> None:
    with SessionFactory() as db:
        projector = SQLAlchemySessionHintProjectorRepository(db=db)
        outbox = SQLAlchemyOutbox(db=db)
        try:
            result = process_due_session_hints_once(projector=projector, outbox=outbox)
            db.commit()
        except Exception:
            db.rollback()
            raise

    logger.info(
        "session hint unlock worker tick claimed=%s succeeded=%s skipped=%s",
        result.claimed_count,
        result.succeeded_count,
        result.skipped_count,
        extra={**log_fields(), "worker_name": WORKER_NAME},
    )


def run_forever(poll_interval_seconds: float = 10.0) -> None:
    run_worker_loop(
        worker_name=WORKER_NAME,
        run_once=run_once,
        poll_interval_seconds=poll_interval_seconds,
        logger=logger,
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
