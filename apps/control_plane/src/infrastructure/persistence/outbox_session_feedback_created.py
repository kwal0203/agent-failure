from datetime import datetime

from pydantic import ValidationError
from sqlalchemy.orm import Session

from apps.contracts.src.schemas import SessionFeedbackCreatedEventPayload
from apps.contracts.src.types import OUTBOX_EVENT_SESSION_FEEDBACK_CREATED
from apps.control_plane.src.application.session_feedback.ports import (
    OutboxSessionFeedbackCreatedPort,
)
from apps.control_plane.src.application.session_feedback.types import (
    PendingSessionFeedbackCreatedEvent,
)

from .outbox_consumer import SQLAlchemyOutboxConsumer


class SQLAlchemyOutboxSessionFeedbackCreated(
    SQLAlchemyOutboxConsumer, OutboxSessionFeedbackCreatedPort
):
    def __init__(self, db: Session) -> None:
        self._db = db

    def claim_pending_session_feedback_created(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingSessionFeedbackCreatedEvent]:
        rows = self._claim_pending_rows(
            event_type=OUTBOX_EVENT_SESSION_FEEDBACK_CREATED,
            limit=limit,
            now=now,
        )

        claimed: list[PendingSessionFeedbackCreatedEvent] = []
        for row in rows:
            requested_at = row.created_at
            try:
                payload = SessionFeedbackCreatedEventPayload.model_validate(row.payload)
                requested_at = payload.created_at
            except ValidationError:
                # Payload validation happens in consumer service; for claim ordering,
                # fallback to row timestamp when payload is malformed.
                pass
            claimed.append(
                PendingSessionFeedbackCreatedEvent(
                    outbox_event_id=row.id,
                    session_id=row.aggregate_id,
                    payload=row.payload,
                    attempt_count=row.attempt_count,
                    requested_at=requested_at,
                )
            )
        return claimed
