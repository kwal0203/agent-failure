from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.outbox_learner_feedback_publisher import (
    SQLAlchemyOutboxLearnerFeedbackPublisher,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemyEvaluatorRepository,
)
from apps.control_plane.src.infrastructure.publishers.websocket_learner_feedback_publisher import (
    WebSocketLearnerFeedbackPublisher,
)
from apps.control_plane.src.interfaces.http.session_manager import (
    WebSocketSessionManager,
)
from apps.control_plane.src.application.evaluator_feedback.service import (
    process_pending_feedback_publish_once,
)

import asyncio
import logging

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


async def run_once(*, session_manager: WebSocketSessionManager) -> None:
    with SessionFactory() as db:
        outbox_repo = SQLAlchemyOutboxLearnerFeedbackPublisher(db=db)
        eval_repo = SQLAlchemyEvaluatorRepository(db=db)
        publisher_repo = WebSocketLearnerFeedbackPublisher(gateway=session_manager)
        result = await process_pending_feedback_publish_once(
            outbox_repo=outbox_repo, eval_repo=eval_repo, publisher=publisher_repo
        )
        logger.info(
            "learner feedback worker tick claimed=%s succeeded=%s failed=%s retried=%s",
            result.claimed_count,
            result.succeeded_count,
            result.failed_count,
            result.retried_count,
        )


async def run_forever(
    *, session_manager: WebSocketSessionManager, polling_interval_seconds: float = 10.0
) -> None:
    while True:
        await run_once(session_manager=session_manager)
        await asyncio.sleep(polling_interval_seconds)
