from datetime import datetime
from sqlalchemy.orm import Session
from typing import Any
from apps.contracts.src.types import OUTBOX_EVENT_SESSION_PUBLISH_FEEDBACK
from apps.control_plane.src.application.evaluator_feedback.ports import (
    OutboxLearnerFeedbackPublishPort,
)
from apps.control_plane.src.application.evaluator_feedback.types import (
    PendingLearnerFeedbackPublishEvent,
)

from .outbox_consumer import SQLAlchemyOutboxConsumer


def _as_datetime(value: Any, field_name: str) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be an ISO-8601 string")

    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid ISO-8601 datetime") from exc


class SQLAlchemyOutboxLearnerFeedbackPublisher(
    SQLAlchemyOutboxConsumer, OutboxLearnerFeedbackPublishPort
):
    def __init__(self, db: Session) -> None:
        self._db = db

    def claim_pending_feedback_publish(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingLearnerFeedbackPublishEvent]:
        rows = self._claim_pending_rows(
            event_type=OUTBOX_EVENT_SESSION_PUBLISH_FEEDBACK,
            limit=limit,
            now=now,
        )

        claimed: list[PendingLearnerFeedbackPublishEvent] = []
        for row in rows:
            payload = row.payload
            requested_at = _as_datetime(payload.get("requested_at"), "requested_at")
            if requested_at is None:
                requested_at = row.created_at

            claimed.append(
                PendingLearnerFeedbackPublishEvent(
                    outbox_event_id=row.id,
                    session_id=row.aggregate_id,
                    attempt_count=row.attempt_count,
                    requested_at=requested_at,
                )
            )

        return claimed
