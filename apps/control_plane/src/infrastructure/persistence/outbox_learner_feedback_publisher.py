from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import UUID
from typing import Any
from apps.control_plane.src.application.evaluator_feedback.ports import (
    OutboxLearnerFeedbackPublishPort,
)
from apps.control_plane.src.application.evaluator_feedback.types import (
    PendingLearnerFeedbackPublishEvent,
)

from .models import OutboxEventModel


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


class SQLAlchemyOutboxLearnerFeedbackPublisher(OutboxLearnerFeedbackPublishPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def claim_pending_feedback_publish(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingLearnerFeedbackPublishEvent]:
        ts = now or datetime.now(timezone.utc)

        rows = (
            self._db.execute(
                select(OutboxEventModel)
                .where(
                    OutboxEventModel.event_type == "session.publish.feedback.v1",
                    OutboxEventModel.status == "pending",
                    OutboxEventModel.available_at <= ts,
                )
                .order_by(OutboxEventModel.created_at.asc())
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
            .scalars()
            .all()
        )

        claimed: list[PendingLearnerFeedbackPublishEvent] = []
        for row in rows:
            row.status = "processing"
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

    def mark_processed(
        self, *, outbox_event_id: UUID, processed_at: datetime | None = None
    ) -> None:
        row = self._db.get(OutboxEventModel, outbox_event_id)
        if row is None:
            return

        row.status = "processed"
        row.processed_at = processed_at or datetime.now(timezone.utc)
        row.last_error = None

    def mark_retryable_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        backoff_seconds: int = 15,
        failed_at: datetime | None = None,
    ) -> None:
        row = self._db.get(OutboxEventModel, outbox_event_id)
        if row is None:
            return

        ts = failed_at or datetime.now(timezone.utc)
        row.status = "pending"
        row.attempt_count = row.attempt_count + 1
        row.available_at = ts + timedelta(seconds=backoff_seconds)
        row.last_error = error_message

    def mark_terminal_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        failed_at: datetime | None = None,
    ) -> None:
        row = self._db.get(OutboxEventModel, outbox_event_id)
        if row is None:
            return

        ts = failed_at or datetime.now(timezone.utc)
        row.status = "failed"
        row.attempt_count = row.attempt_count + 1
        row.processed_at = ts
        row.last_error = error_message
