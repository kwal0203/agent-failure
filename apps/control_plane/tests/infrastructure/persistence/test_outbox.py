from sqlalchemy import func, select
from sqlalchemy.orm import Session
from apps.control_plane.src.infrastructure.persistence.outbox import (
    SQLAlchemyOutbox,
    OutboxEventModel,
)
from datetime import datetime, timezone
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


def test_enqueue_session_hint_unlocked_happy_path(db_session: Session) -> None:
    outbox = SQLAlchemyOutbox(db=db_session)
    session_id = uuid4()
    unlocked_at = datetime(2026, 4, 19, 19, 0, 0, tzinfo=timezone.utc)

    outbox.enqueue_session_hint_unlocked(
        session_id=session_id,
        hint_key="hint_1",
        text="Ask what tools are available.",
        sort_order=0,
        unlocked_at=unlocked_at,
        idempotency_key=f"hint_unlock:{session_id}:hint_1",
    )
    db_session.flush()

    event = db_session.execute(
        select(OutboxEventModel).where(
            OutboxEventModel.aggregate_id == session_id,
            OutboxEventModel.event_type == "session.hint.unlocked.v1",
        )
    ).scalar_one()
    assert event.status == "pending"
    assert event.payload["session_id"] == str(session_id)
    assert event.payload["hint_key"] == "hint_1"
    assert event.payload["text"] == "Ask what tools are available."
    assert event.payload["sort_order"] == 0
    assert event.payload["idempotency_key"] == f"hint_unlock:{session_id}:hint_1"


def test_enqueue_session_hint_unlocked_is_idempotent_by_key(
    db_session: Session,
) -> None:
    outbox = SQLAlchemyOutbox(db=db_session)
    session_id = uuid4()
    idempotency_key = f"hint_unlock:{session_id}:hint_1"
    unlocked_at = datetime(2026, 4, 19, 19, 0, 0, tzinfo=timezone.utc)

    outbox.enqueue_session_hint_unlocked(
        session_id=session_id,
        hint_key="hint_1",
        text="Hint 1",
        sort_order=0,
        unlocked_at=unlocked_at,
        idempotency_key=idempotency_key,
    )
    outbox.enqueue_session_hint_unlocked(
        session_id=session_id,
        hint_key="hint_1",
        text="Hint 1 duplicate",
        sort_order=0,
        unlocked_at=unlocked_at,
        idempotency_key=idempotency_key,
    )
    db_session.flush()

    count = db_session.execute(
        select(func.count())
        .select_from(OutboxEventModel)
        .where(
            OutboxEventModel.aggregate_id == session_id,
            OutboxEventModel.event_type == "session.hint.unlocked.v1",
        )
    ).scalar_one()
    assert count == 1


def test_enqueue_session_completed_happy_path_preserves_nullable_payload_fields(
    db_session: Session,
) -> None:
    outbox = SQLAlchemyOutbox(db=db_session)
    session_id = uuid4()
    lab_id = uuid4()
    lab_version_id = uuid4()

    outbox.enqueue_session_completed(
        session_id=session_id,
        lab_id=lab_id,
        lab_version_id=lab_version_id,
        outcome="completed_success",
        completion_reason_code=None,
        trigger_event_index=None,
        idempotency_key=f"session_completed:{session_id}:completed_success:none:none",
    )
    db_session.flush()

    event = db_session.execute(
        select(OutboxEventModel).where(
            OutboxEventModel.aggregate_id == session_id,
            OutboxEventModel.event_type == "session.completed.v1",
        )
    ).scalar_one()

    assert event.status == "pending"
    payload = event.payload
    assert payload["session_id"] == str(session_id)
    assert payload["lab_id"] == str(lab_id)
    assert payload["lab_version_id"] == str(lab_version_id)
    assert payload["outcome"] == "completed_success"
    assert "completion_reason_code" in payload
    assert payload["completion_reason_code"] is None
    assert "trigger_event_index" in payload
    assert payload["trigger_event_index"] is None


def test_enqueue_session_completed_is_idempotent_by_key(db_session: Session) -> None:
    outbox = SQLAlchemyOutbox(db=db_session)
    session_id = uuid4()
    idempotency_key = f"session_completed:{session_id}:completed_failure:timeout:17"

    outbox.enqueue_session_completed(
        session_id=session_id,
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        outcome="completed_failure",
        completion_reason_code="TIMEOUT",
        trigger_event_index=17,
        idempotency_key=idempotency_key,
    )
    outbox.enqueue_session_completed(
        session_id=session_id,
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        outcome="completed_failure",
        completion_reason_code="IGNORED_DUPLICATE",
        trigger_event_index=999,
        idempotency_key=idempotency_key,
    )
    db_session.flush()

    count = db_session.execute(
        select(func.count())
        .select_from(OutboxEventModel)
        .where(
            OutboxEventModel.aggregate_id == session_id,
            OutboxEventModel.event_type == "session.completed.v1",
        )
    ).scalar_one()
    assert count == 1
