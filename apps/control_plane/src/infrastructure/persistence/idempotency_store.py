from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.application.common.ports import IdempotencyStore

from apps.control_plane.src.application.session_lifecycle.schemas import (
    TransitionResult,
)
from apps.control_plane.src.application.session_create.schemas import (
    CreateSessionResult,
)
from sqlalchemy.orm import Session
from sqlalchemy import select
from .models import IdempotencyRecordModel, SessionTransitionEventModel
from .errors import DataIntegrityError


class SQLAlchemyTransitionIdempotencyStore(IdempotencyStore[TransitionResult]):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, operation: str, key: str) -> TransitionResult | None:
        record = self._db.execute(
            statement=select(IdempotencyRecordModel).where(
                IdempotencyRecordModel.operation == operation,
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

    def save(self, operation: str, key: str, result: TransitionResult) -> None:
        record = IdempotencyRecordModel(
            operation=operation,
            idempotency_key=key,
            session_id=result.session_id,
            transition_id=result.transition_id,
            response_payload=None,
        )
        self._db.add(instance=record)


class SQLAlchemyCreateSessionIdempotencyStore(IdempotencyStore[CreateSessionResult]):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, operation: str, key: str) -> CreateSessionResult | None:
        record = self._db.execute(
            select(IdempotencyRecordModel).where(
                IdempotencyRecordModel.operation == operation,
                IdempotencyRecordModel.idempotency_key == key,
            )
        ).scalar_one_or_none()

        if record is None:
            return None

        if record.session_id is None or record.response_payload is None:
            raise DataIntegrityError

        return CreateSessionResult.model_validate(record.response_payload)

    def save(self, operation: str, key: str, result: CreateSessionResult) -> None:
        record = IdempotencyRecordModel(
            operation=operation,
            idempotency_key=key,
            session_id=result.session_id,
            transition_id=None,
            response_payload=result.model_dump(mode="json"),
        )
        self._db.add(instance=record)
