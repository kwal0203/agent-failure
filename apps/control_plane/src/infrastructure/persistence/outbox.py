from typing import Mapping
from uuid import UUID
from sqlalchemy.orm import Session

from apps.control_plane.src.application.session_lifecycle.ports import Outbox
from apps.control_plane.src.domain.session_lifecycle.state_machine import (
    SessionState,
    Trigger,
)
from .models import OutboxEventModel


class SQLAlchemyOutbox(Outbox):
    def __init__(self, db: Session) -> None:
        self._db = db

    def enqueue_for_transition(
        self,
        session_id: UUID,
        prev_state: SessionState,
        next_state: SessionState,
        trigger: Trigger,
        metadata: Mapping[str, object],
        transition_id: UUID,
    ) -> None:
        payload: dict[str, object] = {
            "session_id": str(session_id),
            "prev_state": prev_state.value,
            "next_state": next_state.value,
            "trigger": trigger.value,
            "metadata": dict(metadata),
            "transition_id": str(transition_id),
        }

        event = OutboxEventModel(
            event_type="session.transitioned.v1",
            aggregate_id=session_id,
            payload=payload,
        )
        self._db.add(event)
