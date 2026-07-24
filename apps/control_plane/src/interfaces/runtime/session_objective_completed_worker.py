import logging
from apps.control_plane.src.application.common.observability import (
    log_fields,
)
from apps.control_plane.src.interfaces.runtime.worker_loop import run_worker_loop

from apps.control_plane.src.application.session_objectives.service import (
    process_pending_objective_completed_once,
)
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.outbox import SQLAlchemyOutbox
from apps.control_plane.src.infrastructure.persistence.outbox_session_objective_completed import (
    SQLAlchemyOutboxSessionObjectiveCompleted,
)
from apps.control_plane.src.infrastructure.persistence.session_objectives_repository import (
    SQLAlchemyLabObjectiveTemplateRepository,
    SQLAlchemySessionObjectiveWriterRepository,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionRepository,
)

logger = logging.getLogger(__name__)
WORKER_NAME = "session_objective_completed_worker"


def run_once() -> None:
    with SessionFactory() as db:
        outbox_repo = SQLAlchemyOutboxSessionObjectiveCompleted(db=db)
        event_outbox_repo = SQLAlchemyOutbox(db=db)
        template_reader = SQLAlchemyLabObjectiveTemplateRepository(db=db)
        objective_writer = SQLAlchemySessionObjectiveWriterRepository(db=db)
        completion_writer = SQLAlchemySessionRepository(db=db)
        try:
            result = process_pending_objective_completed_once(
                outbox_repo=outbox_repo,
                event_outbox_repo=event_outbox_repo,
                template_reader=template_reader,
                objective_writer=objective_writer,
                completion_writer=completion_writer,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

    logger.info(
        "session objective completed worker tick claimed=%s succeeded=%s failed=%s retried=%s",
        result.claimed_count,
        result.succeeded_count,
        result.failed_count,
        result.retried_count,
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
