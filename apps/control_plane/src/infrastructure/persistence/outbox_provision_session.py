from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import UUID

from apps.control_plane.src.application.orchestrator.ports import (
    OutboxProvisioningSessionPort,
)
from apps.control_plane.src.application.orchestrator.types import (
    PendingProvisioningEvent,
)
from .models import OutboxEventModel


# Consumer (outbox.py and outbox_create_session.py are producers that write to the queue)
class SQLAlchemyOutboxProvisionSession(OutboxProvisioningSessionPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def claim_pending_provisioning(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingProvisioningEvent]:
        ts = now or datetime.now(timezone.utc)

        rows = (
            self._db.execute(
                select(OutboxEventModel)
                .where(
                    OutboxEventModel.event_type == "session.provisioning.v1",
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

        claimed: list[PendingProvisioningEvent] = []
        for row in rows:
            row.status = "processing"
            claimed.append(
                PendingProvisioningEvent(
                    outbox_event_id=row.id,
                    session_id=row.aggregate_id,
                    payload=row.payload,
                    attempt_count=row.attempt_count,
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
