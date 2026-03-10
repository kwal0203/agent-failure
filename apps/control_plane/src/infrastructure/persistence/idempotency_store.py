from uuid import UUID
from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.application.session_lifecycle.ports import IdempotencyStore
from apps.control_plane.src.application.session_lifecycle.schemas import (
    TransitionResult,
)
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import IdempotencyRecordModel, SessionTransitionEventModel
from .errors import DataIntegrityError


class PostgresIdempotencyStore(IdempotencyStore):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, key: UUID) -> TransitionResult | None:
        record = self._db.execute(
            statement=select(IdempotencyRecordModel).where(
                IdempotencyRecordModel.operation == "transition_session",
                IdempotencyRecordModel.idempotency_key == key,
            )
        ).scalar_one_or_none()
        if record is None:
            return None

        if record.transition_id is None or record.session_id is None:
            raise DataIntegrityError

        event: SessionTransitionEventModel | None = self._db.execute(
            statement=select(SessionTransitionEventModel).where(
                SessionTransitionEventModel.id == record.transition_id
            )
        ).scalar_one_or_none()
        if event is None:
            raise DataIntegrityError

        return TransitionResult(
            transition_id=event.id,
            session_id=event.session_id,
            prev_state=SessionState(event.prev_state),
            next_state=SessionState(event.next_state),
        )

    def save(self, key: UUID, result: TransitionResult) -> None:
        record = IdempotencyRecordModel(
            operation="transition_session",
            idempotency_key=key,
            session_id=result.session_id,
            transition_id=result.transition_id,
            response_payload=None,
        )
        self._db.add(instance=record)
