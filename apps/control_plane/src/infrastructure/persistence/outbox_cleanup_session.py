from datetime import datetime
from apps.contracts.src.types import OUTBOX_EVENT_SESSION_CLEANUP_REQUESTED

from apps.control_plane.src.application.orchestrator.ports import (
    OutboxCleanupSessionPort,
)
from sqlalchemy.orm import Session

from apps.control_plane.src.application.orchestrator.types import PendingCleanupEvent

from .outbox_consumer import SQLAlchemyOutboxConsumer


class SQLAlchemyCleanupSession(SQLAlchemyOutboxConsumer, OutboxCleanupSessionPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def claim_pending_cleanup(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingCleanupEvent]:
        rows = self._claim_pending_rows(
            event_type=OUTBOX_EVENT_SESSION_CLEANUP_REQUESTED,
            limit=limit,
            now=now,
        )

        claimed: list[PendingCleanupEvent] = []
        for row in rows:
            claimed.append(
                PendingCleanupEvent(
                    outbox_event_id=row.id,
                    session_id=row.aggregate_id,
                    payload=row.payload,
                    attempt_count=row.attempt_count,
                )
            )

        return claimed
