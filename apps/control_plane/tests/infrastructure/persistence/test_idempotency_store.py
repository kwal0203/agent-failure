from uuid import uuid4, UUID

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.control_plane.src.application.session_lifecycle.schemas import (
    TransitionResult,
)
from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.errors import DataIntegrityError
from apps.control_plane.src.infrastructure.persistence.idempotency_store import (
    PostgresIdempotencyStore,
)
from apps.control_plane.src.infrastructure.persistence.models import (
    IdempotencyRecordModel,
    SessionModel,
    SessionTransitionEventModel,
)


def _insert_session(
    db_session: Session, state: SessionState = SessionState.CREATED
) -> SessionModel:
    row = SessionModel(
        id=uuid4(),
        state=state.value,
        last_transition_actor="seed",
        last_transition_reason=None,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _insert_transition_event(
    db_session: Session,
    session_id: UUID,
    prev_state: SessionState = SessionState.CREATED,
    next_state: SessionState = SessionState.PROVISIONING,
) -> SessionTransitionEventModel:
    event = SessionTransitionEventModel(
        id=uuid4(),
        session_id=session_id,
        prev_state=prev_state.value,
        next_state=next_state.value,
        trigger="LAUNCH_SUCCEEDED",
        actor="system",
        event_metadata={},
        idempotency_key=uuid4(),
    )
    db_session.add(event)
    db_session.flush()
    return event


def test_get_returns_none_when_key_missing(db_session: Session) -> None:
    store = PostgresIdempotencyStore(db=db_session)
    assert store.get(uuid4()) is None


def test_save_then_get_returns_transition_result(db_session: Session) -> None:
    store = PostgresIdempotencyStore(db=db_session)
    session = _insert_session(db_session)
    event = _insert_transition_event(db_session, session.id)

    key = uuid4()
    result = TransitionResult(
        transition_id=event.id,
        session_id=session.id,
        prev_state=SessionState.CREATED,
        next_state=SessionState.PROVISIONING,
    )

    store.save(key=key, result=result)
    db_session.flush()

    loaded = store.get(key)
    assert loaded is not None
    assert loaded.transition_id == result.transition_id
    assert loaded.session_id == result.session_id
    assert loaded.prev_state == result.prev_state
    assert loaded.next_state == result.next_state


def test_save_enforces_unique_operation_key(db_session: Session) -> None:
    store = PostgresIdempotencyStore(db=db_session)
    session = _insert_session(db_session)
    event = _insert_transition_event(db_session, session.id)
    key = uuid4()

    result = TransitionResult(
        transition_id=event.id,
        session_id=session.id,
        prev_state=SessionState.CREATED,
        next_state=SessionState.PROVISIONING,
    )

    store.save(key=key, result=result)
    db_session.flush()

    store.save(key=key, result=result)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_get_raises_data_integrity_when_transition_id_missing(
    db_session: Session,
) -> None:
    store = PostgresIdempotencyStore(db=db_session)
    session = _insert_session(db_session)
    key = uuid4()

    record = IdempotencyRecordModel(
        operation="transition_session",
        idempotency_key=key,
        session_id=session.id,
        transition_id=None,
        response_payload=None,
    )
    db_session.add(record)
    db_session.flush()

    with pytest.raises(DataIntegrityError):
        store.get(key)


def test_save_rejects_missing_transition_event_fk(db_session: Session) -> None:
    session = _insert_session(db_session)

    record = IdempotencyRecordModel(
        operation="transition_session",
        idempotency_key=uuid4(),
        session_id=session.id,
        transition_id=uuid4(),  # references non-existent transition row
        response_payload=None,
    )
    db_session.add(record)

    with pytest.raises(IntegrityError):
        db_session.flush()
