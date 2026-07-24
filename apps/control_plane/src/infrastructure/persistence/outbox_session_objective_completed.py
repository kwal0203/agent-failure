from datetime import datetime

from pydantic import ValidationError
from sqlalchemy.orm import Session
from apps.contracts.src.types import OUTBOX_EVENT_SESSION_OBJECTIVE_COMPLETED

from apps.control_plane.src.application.session_objectives.ports import (
    OutboxSessionObjectiveCompletedPort,
)
from apps.control_plane.src.application.session_objectives.schemas import (
    ObjectiveCompletedEventPayload,
)
from apps.control_plane.src.application.session_objectives.types import (
    PendingSessionObjectiveCompletedEvent,
)

from .outbox_consumer import SQLAlchemyOutboxConsumer


class SQLAlchemyOutboxSessionObjectiveCompleted(
    SQLAlchemyOutboxConsumer, OutboxSessionObjectiveCompletedPort
):
    def __init__(self, db: Session) -> None:
        self._db = db

    def claim_pending_objective_completed(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingSessionObjectiveCompletedEvent]:
        rows = self._claim_pending_rows(
            event_type=OUTBOX_EVENT_SESSION_OBJECTIVE_COMPLETED,
            limit=limit,
            now=now,
        )

        claimed: list[PendingSessionObjectiveCompletedEvent] = []
        for row in rows:
            requested_at = row.created_at
            try:
                payload = ObjectiveCompletedEventPayload.model_validate(row.payload)
                requested_at = payload.occurred_at
            except ValidationError:
                # Payload validation happens in consumer service; for claim ordering,
                # fallback to row timestamp when payload is malformed.
                pass
            claimed.append(
                PendingSessionObjectiveCompletedEvent(
                    outbox_event_id=row.id,
                    session_id=row.aggregate_id,
                    payload=row.payload,
                    attempt_count=row.attempt_count,
                    requested_at=requested_at,
                )
            )

        return claimed
