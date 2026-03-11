from sqlalchemy import func, select
from sqlalchemy.orm import Session
from apps.control_plane.src.infrastructure.persistence.outbox import (
    SQLAlchemyOutbox,
    OutboxEventModel,
)
from apps.control_plane.src.domain.session_lifecycle.state_machine import (
    SessionState,
    Trigger,
)
from uuid import uuid4
import pytest


def test_enqueue_for_transition_happy_path(db_session: Session) -> None:
    outbox = SQLAlchemyOutbox(db=db_session)

    session_id = uuid4()
    transition_id = uuid4()
    outbox.enqueue_for_transition(
        session_id=session_id,
        prev_state=SessionState.CREATED,
        next_state=SessionState.PROVISIONING,
        trigger=Trigger.LAUNCH_SUCCEEDED,
        metadata={"reason_code": "launch_succeeded"},
        transition_id=transition_id,
    )
    db_session.flush()

    event = db_session.execute(
        select(OutboxEventModel).where(
            OutboxEventModel.aggregate_id == session_id,
            OutboxEventModel.event_type == "session.transitioned.v1",
        )
    ).scalar_one()

    assert event.status == "pending"
    assert event.attempt_count == 0
    assert event.payload["session_id"] == str(session_id)
    assert event.payload["prev_state"] == SessionState.CREATED.value
    assert event.payload["next_state"] == SessionState.PROVISIONING.value
    assert event.payload["trigger"] == Trigger.LAUNCH_SUCCEEDED.value
    assert event.payload["transition_id"] == str(transition_id)

    metadata = event.payload["metadata"]
    assert isinstance(metadata, dict)
    assert metadata["reason_code"] == "launch_succeeded"


def test_enqueue_sets_default_fields(db_session: Session) -> None:
    outbox = SQLAlchemyOutbox(db=db_session)

    session_id = uuid4()
    transition_id = uuid4()

    outbox.enqueue_for_transition(
        session_id=session_id,
        prev_state=SessionState.CREATED,
        next_state=SessionState.PROVISIONING,
        trigger=Trigger.LAUNCH_SUCCEEDED,
        metadata={"reason_code": "launch_succeeded"},
        transition_id=transition_id,
    )
    db_session.flush()

    event = db_session.execute(
        select(OutboxEventModel).where(
            OutboxEventModel.aggregate_id == session_id,
            OutboxEventModel.event_type == "session.transitioned.v1",
        )
    ).scalar_one()

    assert event.status == "pending"
    assert event.attempt_count == 0
    assert event.processed_at is None
    assert event.last_error is None


def test_enqueue_serializes_enums_and_uuids(db_session: Session) -> None:
    outbox = SQLAlchemyOutbox(db=db_session)

    session_id = uuid4()
    transition_id = uuid4()
    outbox.enqueue_for_transition(
        session_id=session_id,
        prev_state=SessionState.CREATED,
        next_state=SessionState.PROVISIONING,
        trigger=Trigger.LAUNCH_SUCCEEDED,
        metadata={"reason_code": "launch_succeeded"},
        transition_id=transition_id,
    )
    db_session.flush()

    event = db_session.execute(
        select(OutboxEventModel).where(
            OutboxEventModel.aggregate_id == session_id,
            OutboxEventModel.event_type == "session.transitioned.v1",
        )
    ).scalar_one()
    metadata = event.payload
    assert isinstance(metadata, dict)
    assert isinstance(metadata["session_id"], str)
    assert isinstance(metadata["transition_id"], str)
    assert isinstance(metadata["prev_state"], str)
    assert isinstance(metadata["next_state"], str)
    assert isinstance(metadata["trigger"], str)


def test_enqueue_accepts_empty_metadata(db_session: Session) -> None:
    outbox = SQLAlchemyOutbox(db=db_session)

    session_id = uuid4()
    outbox.enqueue_for_transition(
        session_id=session_id,
        prev_state=SessionState.CREATED,
        next_state=SessionState.PROVISIONING,
        trigger=Trigger.LAUNCH_SUCCEEDED,
        metadata={},
        transition_id=uuid4(),
    )
    db_session.flush()

    event = db_session.execute(
        select(OutboxEventModel).where(
            OutboxEventModel.aggregate_id == session_id,
            OutboxEventModel.event_type == "session.transitioned.v1",
        )
    ).scalar_one()
    payload = event.payload
    assert isinstance(payload, dict)

    meta = payload["metadata"]
    assert isinstance(meta, dict)
    assert meta == {}


def test_enqueue_multiple_events_for_same_session(db_session: Session) -> None:
    outbox = SQLAlchemyOutbox(db=db_session)
    session_id = uuid4()

    outbox.enqueue_for_transition(
        session_id=session_id,
        prev_state=SessionState.CREATED,
        next_state=SessionState.PROVISIONING,
        trigger=Trigger.LAUNCH_SUCCEEDED,
        metadata={"reason_code": "launch_succeeded"},
        transition_id=uuid4(),
    )
    outbox.enqueue_for_transition(
        session_id=session_id,
        prev_state=SessionState.PROVISIONING,
        next_state=SessionState.ACTIVE,
        trigger=Trigger.PROVISIONING_SUCCEEDED,
        metadata={"reason_code": "provisioning_succeeded"},
        transition_id=uuid4(),
    )
    db_session.flush()

    count = db_session.execute(
        select(func.count())
        .select_from(OutboxEventModel)
        .where(OutboxEventModel.aggregate_id == session_id)
    ).scalar_one()
    assert count == 2


def test_enqueue_is_rolled_back_with_transaction(db_session: Session) -> None:
    outbox = SQLAlchemyOutbox(db=db_session)
    session_id = uuid4()

    outbox.enqueue_for_transition(
        session_id=session_id,
        prev_state=SessionState.CREATED,
        next_state=SessionState.PROVISIONING,
        trigger=Trigger.LAUNCH_SUCCEEDED,
        metadata={"reason_code": "launch_succeeded"},
        transition_id=uuid4(),
    )
    db_session.flush()
    db_session.rollback()

    count = db_session.execute(
        select(func.count())
        .select_from(OutboxEventModel)
        .where(OutboxEventModel.aggregate_id == session_id)
    ).scalar_one()
    assert count == 0


def test_enqueue_raises_on_non_json_serializable_metadata(db_session: Session) -> None:
    outbox = SQLAlchemyOutbox(db=db_session)

    outbox.enqueue_for_transition(
        session_id=uuid4(),
        prev_state=SessionState.CREATED,
        next_state=SessionState.PROVISIONING,
        trigger=Trigger.LAUNCH_SUCCEEDED,
        metadata={"bad_value": object()},
        transition_id=uuid4(),
    )

    with pytest.raises(TypeError):
        db_session.flush()
