from datetime import datetime, timedelta, timezone
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.contracts.src.schemas import SessionCompletedEventPayload
from apps.control_plane.src.application.session_completion.ports import (
    OutboxSessionCompletedPort,
)
from apps.control_plane.src.application.session_completion.types import (
    PendingSessionCompletedEvent,
)

from .models import OutboxEventModel

EVENT_TYPE_SESSION_COMPLETED = "session.completed.v1"


class SQLAlchemyOutboxSessionCompleted(OutboxSessionCompletedPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def claim_pending_session_completed(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingSessionCompletedEvent]:
        ts = now or datetime.now(timezone.utc)
        rows = (
            self._db.execute(
                select(OutboxEventModel)
                .where(
                    OutboxEventModel.event_type == EVENT_TYPE_SESSION_COMPLETED,
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

        claimed: list[PendingSessionCompletedEvent] = []
        for row in rows:
            row.status = "processing"
            requested_at = row.created_at
            try:
                payload = SessionCompletedEventPayload.model_validate(row.payload)
                requested_at = payload.occurred_at
            except ValidationError:
                # Payload validation happens in consumer service; for claim ordering,
                # fallback to row timestamp when payload is malformed.
                pass
            claimed.append(
                PendingSessionCompletedEvent(
                    outbox_event_id=row.id,
                    session_id=row.aggregate_id,
                    payload=row.payload,
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
