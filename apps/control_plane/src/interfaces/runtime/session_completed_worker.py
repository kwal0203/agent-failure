import logging
import time
from apps.control_plane.src.application.common.observability import (
    log_fields,
    reset_correlation_id,
    set_correlation_id,
)

from apps.control_plane.src.application.session_completion.service import (
    process_pending_session_completed_once,
)
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.outbox_session_completed import (
    SQLAlchemyOutboxSessionCompleted,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionRepository,
)

logger = logging.getLogger(__name__)
WORKER_NAME = "session_completed_worker"


def run_once() -> None:
    with SessionFactory() as db:
        outbox_repo = SQLAlchemyOutboxSessionCompleted(db=db)
        completion_writer = SQLAlchemySessionRepository(db=db)
        try:
            result = process_pending_session_completed_once(
                outbox_repo=outbox_repo,
                completion_writer=completion_writer,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

    logger.info(
        "session completed worker tick claimed=%s succeeded=%s failed=%s retried=%s",
        result.claimed_count,
        result.succeeded_count,
        result.failed_count,
        result.retried_count,
        extra={**log_fields(), "worker_name": WORKER_NAME},
    )


def run_forever(poll_interval_seconds: float = 10.0) -> None:
    while True:
        token = set_correlation_id(None)
        try:
            run_once()
        except Exception:
            logger.exception(
                "session completed worker tick failed",
                extra={**log_fields(), "worker_name": WORKER_NAME},
            )
        finally:
            reset_correlation_id(token)
        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
