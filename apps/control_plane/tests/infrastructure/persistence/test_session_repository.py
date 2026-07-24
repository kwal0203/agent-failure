from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from apps.control_plane.src.domain.session_lifecycle.state_machine import (
    SessionState,
    Trigger,
)
from apps.control_plane.src.application.orchestrator.types import (
    UpsertSessionRuntimeBindingInput,
)
from apps.control_plane.src.infrastructure.persistence.models import SessionModel
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionRuntimeBindingRepository,
    SQLAlchemySessionRepository,
    SessionTransitionEventModel,
)
from apps.control_plane.src.infrastructure.persistence.errors import StateMismatch
from uuid import uuid4
from datetime import datetime, timezone

import pytest


def _insert_session(
    db_session: Session, state: SessionState = SessionState.CREATED
) -> SessionModel:
    row = SessionModel(
        id=uuid4(),
        owner_user_id=uuid4(),
        state=state,
        last_transition_actor="seed",
        last_transition_reason=None,
    )
    db_session.add(instance=row)
    db_session.flush()
    return row


def test_get_for_update_returns_row(
    repo: SQLAlchemySessionRepository, db_session: Session
) -> None:
    row = _insert_session(db_session=db_session, state=SessionState.CREATED)

    result = repo.get_for_update(session_id=row.id)

    assert result is not None
    assert result.id == row.id
    assert result.state == SessionState.CREATED


def test_get_for_update_returns_none_for_missing(
    repo: SQLAlchemySessionRepository, db_session: Session
) -> None:
    result = repo.get_for_update(session_id=uuid4())
    assert result is None


def test_runtime_binding_represents_missing_url_without_placeholder(
    db_session: Session,
) -> None:
    session = _insert_session(
        db_session=db_session,
        state=SessionState.PROVISIONING,
    )
    repo = SQLAlchemySessionRuntimeBindingRepository(db=db_session)

    repo.upsert_runtime_binding(
        input=UpsertSessionRuntimeBindingInput(
            session_id=session.id,
            runtime_kind="k8s_pod",
            base_url=None,
            status="provisioning",
        )
    )

    binding = repo.get_by_session_id(session_id=session.id)
    assert binding is not None
    assert binding.runtime_kind == "k8s_pod"
    assert binding.base_url is None
    assert binding.status == "provisioning"


def test_ready_runtime_binding_requires_base_url() -> None:
    with pytest.raises(ValueError, match="requires a base URL"):
        UpsertSessionRuntimeBindingInput(
            session_id=uuid4(),
            runtime_kind="k8s_pod",
            base_url=None,
            status="ready",
        )


def test_update_state_happy_path(
    repo: SQLAlchemySessionRepository, db_session: Session
) -> None:
    row = _insert_session(db_session=db_session, state=SessionState.CREATED)

    repo.update_state(
        session_id=row.id,
        from_state=SessionState.CREATED,
        to_state=SessionState.PROVISIONING,
        actor="system",
        reason="launch succeeded",
    )
    db_session.flush()

    refreshed = db_session.get(SessionModel, row.id)
    assert refreshed is not None
    assert refreshed.state == SessionState.PROVISIONING.value
    assert refreshed.last_transition_actor == "system"
    assert refreshed.last_transition_reason == "launch succeeded"


def test_update_state_raises_on_state_mismatch(
    repo: SQLAlchemySessionRepository, db_session: Session
) -> None:
    row = _insert_session(db_session=db_session, state=SessionState.ACTIVE)

    with pytest.raises(StateMismatch):
        repo.update_state(
            session_id=row.id,
            from_state=SessionState.CREATED,
            to_state=SessionState.PROVISIONING,
            actor="system",
            reason=None,
        )


def test_insert_transition_event_persists_and_returns_result(
    repo: SQLAlchemySessionRepository, db_session: Session
) -> None:
    row = _insert_session(db_session=db_session, state=SessionState.CREATED)
    idem_key = str(uuid4())

    result = repo.insert_transition_event(
        session_id=row.id,
        prev_state=SessionState.CREATED,
        next_state=SessionState.PROVISIONING,
        trigger=Trigger.LAUNCH_SUCCEEDED,
        actor="system",
        metadata={"reason_code": "launch_succeeded"},
        idempotency_key=idem_key,
    )
    db_session.flush()

    assert result is not None
    assert result.session_id == row.id
    assert result.prev_state == SessionState.CREATED
    assert result.next_state == SessionState.PROVISIONING

    stored = db_session.execute(
        statement=select(SessionTransitionEventModel).where(
            SessionTransitionEventModel.id == result.transition_id
        )
    ).scalar_one()

    assert stored.session_id == row.id
    assert stored.prev_state == SessionState.CREATED.value
    assert stored.next_state == SessionState.PROVISIONING.value
    assert stored.trigger == Trigger.LAUNCH_SUCCEEDED.value
    assert stored.event_metadata["reason_code"] == "launch_succeeded"


def test_insert_transition_event_enforces_idempotency_uniqueness(
    repo: SQLAlchemySessionRepository, db_session: Session
) -> None:
    row = _insert_session(db_session=db_session, state=SessionState.CREATED)
    idem_key = str(uuid4())

    repo.insert_transition_event(
        session_id=row.id,
        prev_state=SessionState.CREATED,
        next_state=SessionState.PROVISIONING,
        trigger=Trigger.LAUNCH_SUCCEEDED,
        actor="system",
        metadata={"reason_code": "lauch_succeeded"},
        idempotency_key=idem_key,
    )

    with pytest.raises(IntegrityError):
        repo.insert_transition_event(
            session_id=row.id,
            prev_state=SessionState.PROVISIONING,
            next_state=SessionState.ACTIVE,
            trigger=Trigger.PROVISIONING_SUCCEEDED,
            actor="system",
            metadata={"reason_code": "provisioning_succeeded"},
            idempotency_key=idem_key,
        )

    db_session.rollback()


def test_mark_completion_if_in_progress_is_idempotent(
    repo: SQLAlchemySessionRepository, db_session: Session
) -> None:
    row = _insert_session(db_session=db_session, state=SessionState.ACTIVE)
    first_completed_at = datetime.now(timezone.utc)

    changed = repo.mark_completion_if_in_progress(
        session_id=row.id,
        completion_status="completed_success",
        completed_at=first_completed_at,
        completion_reason_code="ALL_OBJECTIVES_COMPLETED",
    )
    db_session.flush()
    db_session.expire_all()

    first = db_session.get(SessionModel, row.id)
    assert changed is True
    assert first is not None
    assert first.completion_status == "completed_success"
    assert first.completed_at == first_completed_at
    assert first.completion_reason_code == "ALL_OBJECTIVES_COMPLETED"

    second_changed = repo.mark_completion_if_in_progress(
        session_id=row.id,
        completion_status="completed_failure",
        completed_at=datetime.now(timezone.utc),
        completion_reason_code="SHOULD_NOT_APPLY",
    )
    db_session.flush()
    db_session.expire_all()

    second = db_session.get(SessionModel, row.id)
    assert second_changed is False
    assert second is not None
    assert second.completion_status == "completed_success"
    assert second.completed_at == first_completed_at
    assert second.completion_reason_code == "ALL_OBJECTIVES_COMPLETED"
