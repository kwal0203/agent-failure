from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import OutboxEventModel


class SQLAlchemyOutboxConsumer:
    """Shared row lifecycle for durable, transactional outbox consumers.

    Claiming only changes rows in the caller's current database transaction.
    Payload parsing and dispatch remain in each event-specific adapter/service
    so their validation and transaction boundaries stay visible.
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def _claim_pending_rows(
        self,
        *,
        event_type: str,
        limit: int,
        now: datetime | None,
    ) -> list[OutboxEventModel]:
        timestamp = now or datetime.now(timezone.utc)
        rows = list(
            self._db.execute(
                select(OutboxEventModel)
                .where(
                    OutboxEventModel.event_type == event_type,
                    OutboxEventModel.status == "pending",
                    OutboxEventModel.available_at <= timestamp,
                )
                .order_by(OutboxEventModel.created_at.asc())
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
            .scalars()
            .all()
        )
        for row in rows:
            row.status = "processing"
        return rows

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
        timestamp = failed_at or datetime.now(timezone.utc)
        row.status = "pending"
        row.attempt_count += 1
        row.available_at = timestamp + timedelta(seconds=backoff_seconds)
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
        timestamp = failed_at or datetime.now(timezone.utc)
        row.status = "failed"
        row.attempt_count += 1
        row.processed_at = timestamp
        row.last_error = error_message
