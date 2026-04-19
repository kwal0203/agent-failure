import logging
import time
from datetime import datetime, timezone

from apps.control_plane.src.application.session_hints.service import (
    process_due_session_hints_once,
)
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.outbox import SQLAlchemyOutbox
from apps.control_plane.src.infrastructure.persistence.session_hints_repository import (
    SQLAlchemySessionHintProjectorRepository,
)
from apps.control_plane.src.infrastructure.persistence.worker_heartbeat_repository import (
    SQLAlchemyWorkerHeartbeatRepository,
)

logger = logging.getLogger(__name__)


def run_once() -> None:
    ts = datetime.now(timezone.utc)
    heartbeat_repo = SQLAlchemyWorkerHeartbeatRepository()
    heartbeat_repo.record_tick(worker_name="session_hint_unlock_worker", at=ts)

    with SessionFactory() as db:
        projector = SQLAlchemySessionHintProjectorRepository(db=db)
        outbox = SQLAlchemyOutbox(db=db)
        try:
            result = process_due_session_hints_once(projector=projector, outbox=outbox)
            db.commit()
            heartbeat_repo.record_success(
                worker_name="session_hint_unlock_worker",
                at=datetime.now(timezone.utc),
            )
        except Exception as exc:
            db.rollback()
            heartbeat_repo.record_error(
                worker_name="session_hint_unlock_worker",
                at=datetime.now(timezone.utc),
                error_message=str(exc),
            )
            raise

    logger.info(
        "session hint unlock worker tick claimed=%s succeeded=%s skipped=%s",
        result.claimed_count,
        result.succeeded_count,
        result.skipped_count,
    )


def run_forever(poll_interval_seconds: float = 10.0) -> None:
    while True:
        try:
            run_once()
        except Exception:
            logger.exception("session hint unlock worker tick failed")
        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
