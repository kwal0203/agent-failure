from datetime import datetime
from sqlalchemy.orm import Session
from apps.contracts.src.types import OUTBOX_EVENT_SESSION_PROVISIONING

from apps.control_plane.src.application.orchestrator.ports import (
    OutboxProvisioningSessionPort,
)
from apps.control_plane.src.application.orchestrator.types import (
    PendingProvisioningEvent,
)
from .outbox_consumer import SQLAlchemyOutboxConsumer


# Consumer (outbox.py and outbox_create_session.py are producers that write to the queue)
class SQLAlchemyOutboxProvisionSession(
    SQLAlchemyOutboxConsumer, OutboxProvisioningSessionPort
):
    def __init__(self, db: Session) -> None:
        self._db = db

    def claim_pending_provisioning(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingProvisioningEvent]:
        rows = self._claim_pending_rows(
            event_type=OUTBOX_EVENT_SESSION_PROVISIONING,
            limit=limit,
            now=now,
        )

        claimed: list[PendingProvisioningEvent] = []
        for row in rows:
            claimed.append(
                PendingProvisioningEvent(
                    outbox_event_id=row.id,
                    session_id=row.aggregate_id,
                    payload=row.payload,
                    attempt_count=row.attempt_count,
                )
            )

        return claimed
