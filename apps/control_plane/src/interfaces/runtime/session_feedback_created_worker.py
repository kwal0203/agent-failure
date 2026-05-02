import logging
import time
from apps.control_plane.src.application.common.observability import (
    log_fields,
    reset_correlation_id,
    set_correlation_id,
)

from apps.control_plane.src.application.session_feedback.service import (
    process_pending_session_feedback_created_once,
)
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.outbox_session_feedback_created import (
    SQLAlchemyOutboxSessionFeedbackCreated,
)
from apps.control_plane.src.infrastructure.persistence.session_feedback_repository import (
    SQLAlchemySessionFeedbackRepository,
)

logger = logging.getLogger(__name__)
WORKER_NAME = "session_feedback_created_worker"


def run_once() -> None:
    with SessionFactory() as db:
        outbox_repo = SQLAlchemyOutboxSessionFeedbackCreated(db=db)
        feedback_repo = SQLAlchemySessionFeedbackRepository(db=db)
        try:
            result = process_pending_session_feedback_created_once(
                outbox_repo=outbox_repo,
                feedback_repo=feedback_repo,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

    logger.info(
        "session feedback created worker tick claimed=%s succeeded=%s failed=%s retried=%s",
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
                "session feedback created worker tick failed",
                extra={**log_fields(), "worker_name": WORKER_NAME},
            )
        finally:
            reset_correlation_id(token)
        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
