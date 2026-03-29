from datetime import datetime
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

    def enqueue_for_cleanup(
        self,
        session_id: UUID,
        runtime_id: str | None,
        terminal_state: str | None,
        reason_code: str | None,
        requested_at: datetime | None,
    ) -> None:
        payload: dict[str, object] = {
            "session_id": str(session_id),
            "runtime_id": runtime_id,
            "terminal_state": terminal_state,
            "reason_code": reason_code,
            "requested_at": requested_at.isoformat() if requested_at else None,
        }

        event = OutboxEventModel(
            event_type="session.cleanup.requested.v1",
            aggregate_id=session_id,
            payload=payload,
        )

        self._db.add(event)

    def enqueue_for_evaluator(
        self,
        *,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        evaluator_version: int,
        start_event_index: int,
        end_event_index: int,
        requested_at: datetime | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "lab_id": str(lab_id),
            "lab_version_id": str(lab_version_id),
            "evaluator_version": evaluator_version,
            "start_event_index": start_event_index,
            "end_event_index": end_event_index,
            "requested_at": requested_at.isoformat() if requested_at else None,
        }

        event = OutboxEventModel(
            event_type="session.evaluate.requested.v1",
            aggregate_id=session_id,
            payload=payload,
        )

        self._db.add(event)

    def enqueue_learner_feedback_publish_request(
        self,
        *,
        session_id: UUID,
        requested_at: datetime | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "session_id": str(session_id),
            "published_at": requested_at.isoformat() if requested_at else None,
        }

        event = OutboxEventModel(
            event_type="session.publish.feedback.v1",
            aggregate_id=session_id,
            payload=payload,
        )

        self._db.add(event)
