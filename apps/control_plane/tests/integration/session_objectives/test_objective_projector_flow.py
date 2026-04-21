from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.control_plane.src.application.session_objectives.service import (
    process_pending_objective_completed_once,
)
from apps.control_plane.src.infrastructure.persistence.models import (
    OutboxEventModel,
    SessionModel,
    SessionObjectiveModel,
)
from apps.control_plane.src.infrastructure.persistence.outbox_session_objective_completed import (
    SQLAlchemyOutboxSessionObjectiveCompleted,
)
from apps.control_plane.src.infrastructure.persistence.session_objectives_repository import (
    SQLAlchemySessionObjectiveWriterRepository,
)


def _seed_session(
    db_session: Session,
    *,
    lab_id=None,
    lab_version_id=None,
) -> SessionModel:
    resolved_lab_id = UUID_LAB_2 if lab_id is None else lab_id
    resolved_lab_version_id = (
        UUID_LAB_2_VERSION if lab_version_id is None else lab_version_id
    )
    session = SessionModel(
        id=uuid4(),
        lab_id=resolved_lab_id,
        lab_version_id=resolved_lab_version_id,
        owner_user_id=uuid4(),
        state="ACTIVE",
        last_transition_actor="test",
        last_transition_reason="test_seed",
        lab_difficulty="medium",
    )
    db_session.add(session)
    db_session.flush()
    return session


def _seed_session_objective(
    db_session: Session,
    *,
    session_id,
    objective_key: str,
    label: str,
    sort_order: int,
) -> None:
    db_session.add(
        SessionObjectiveModel(
            session_id=session_id,
            objective_key=objective_key,
            label=label,
            status="pending",
            sort_order=sort_order,
            completed_at=None,
        )
    )


def _seed_objective_completed_event(
    db_session: Session,
    *,
    session_id,
    objective_key: str,
    occurred_at: datetime,
    idempotency_key: str,
    trigger_event_index: int,
    lab_id=None,
    lab_version_id=None,
) -> None:
    resolved_lab_id = UUID_LAB_2 if lab_id is None else lab_id
    resolved_lab_version_id = (
        UUID_LAB_2_VERSION if lab_version_id is None else lab_version_id
    )
    db_session.add(
        OutboxEventModel(
            event_type="session.objective.completed.v1",
            aggregate_id=session_id,
            status="pending",
            payload={
                "session_id": str(session_id),
                "lab_id": str(resolved_lab_id),
                "lab_version_id": str(resolved_lab_version_id),
                "objective_key": objective_key,
                "reason_code": "TEST_REASON",
                "trigger_event_index": trigger_event_index,
                "occurred_at": occurred_at.isoformat(),
                "idempotency_key": idempotency_key,
                "source": "evaluator",
                "evaluator_version": 1,
            },
        )
    )


UUID_LAB_2 = uuid4()
UUID_LAB_2_VERSION = uuid4()
UUID_LAB_3 = uuid4()
UUID_LAB_3_VERSION = uuid4()


def test_objective_projector_completes_all_lab2_objectives(db_session: Session) -> None:
    session = _seed_session(db_session)
    _seed_session_objective(
        db_session,
        session_id=session.id,
        objective_key="unsafe_tool_invocation_triggered",
        label="Unsafe Tool Invocation Triggered",
        sort_order=0,
    )
    _seed_session_objective(
        db_session,
        session_id=session.id,
        objective_key="security_boundary_crossed",
        label="Security Boundary Crossed",
        sort_order=1,
    )
    _seed_session_objective(
        db_session,
        session_id=session.id,
        objective_key="critical_file_deleted",
        label="Critical File Deleted",
        sort_order=2,
    )
    now = datetime.now(timezone.utc)
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key="unsafe_tool_invocation_triggered",
        occurred_at=now,
        idempotency_key=f"objective:{session.id}:unsafe_tool_invocation_triggered:10",
        trigger_event_index=10,
    )
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key="security_boundary_crossed",
        occurred_at=now,
        idempotency_key=f"objective:{session.id}:security_boundary_crossed:11",
        trigger_event_index=11,
    )
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key="critical_file_deleted",
        occurred_at=now,
        idempotency_key=f"objective:{session.id}:critical_file_deleted:12",
        trigger_event_index=12,
    )
    db_session.flush()

    result = process_pending_objective_completed_once(
        outbox_repo=SQLAlchemyOutboxSessionObjectiveCompleted(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
    )
    db_session.flush()

    assert result.claimed_count == 3
    assert result.succeeded_count == 3
    assert result.failed_count == 0
    assert result.retried_count == 0

    objective_rows = (
        db_session.execute(
            select(SessionObjectiveModel)
            .where(SessionObjectiveModel.session_id == session.id)
            .order_by(SessionObjectiveModel.sort_order.asc())
        )
        .scalars()
        .all()
    )
    assert len(objective_rows) == 3
    assert all(row.status == "complete" for row in objective_rows)
    assert all(row.completed_at is not None for row in objective_rows)


def test_objective_projector_duplicate_replay_is_no_op(db_session: Session) -> None:
    session = _seed_session(db_session)
    _seed_session_objective(
        db_session,
        session_id=session.id,
        objective_key="critical_file_deleted",
        label="Critical File Deleted",
        sort_order=0,
    )
    first_occurred_at = datetime(2026, 4, 20, 18, 0, 0, tzinfo=timezone.utc)
    replay_occurred_at = datetime(2026, 4, 20, 18, 5, 0, tzinfo=timezone.utc)
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key="critical_file_deleted",
        occurred_at=first_occurred_at,
        idempotency_key=f"objective:{session.id}:critical_file_deleted:21",
        trigger_event_index=21,
    )
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key="critical_file_deleted",
        occurred_at=replay_occurred_at,
        idempotency_key=f"objective:{session.id}:critical_file_deleted:22",
        trigger_event_index=22,
    )
    db_session.flush()

    result = process_pending_objective_completed_once(
        outbox_repo=SQLAlchemyOutboxSessionObjectiveCompleted(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
    )
    db_session.flush()

    assert result.claimed_count == 2
    assert result.succeeded_count == 2
    assert result.failed_count == 0
    assert result.retried_count == 0

    objective_row = (
        db_session.execute(
            select(SessionObjectiveModel).where(
                SessionObjectiveModel.session_id == session.id,
                SessionObjectiveModel.objective_key == "critical_file_deleted",
            )
        )
        .scalars()
        .one()
    )
    assert objective_row.status == "complete"
    # Replay should not overwrite the first completion timestamp.
    assert objective_row.completed_at == first_occurred_at


def test_objective_projector_lab2_negative_path_does_not_complete_delete(
    db_session: Session,
) -> None:
    session = _seed_session(db_session)
    _seed_session_objective(
        db_session,
        session_id=session.id,
        objective_key="unsafe_tool_invocation_triggered",
        label="Unsafe Tool Invocation Triggered",
        sort_order=0,
    )
    _seed_session_objective(
        db_session,
        session_id=session.id,
        objective_key="security_boundary_crossed",
        label="Security Boundary Crossed",
        sort_order=1,
    )
    _seed_session_objective(
        db_session,
        session_id=session.id,
        objective_key="critical_file_deleted",
        label="Critical File Deleted",
        sort_order=2,
    )

    now = datetime.now(timezone.utc)
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key="unsafe_tool_invocation_triggered",
        occurred_at=now,
        idempotency_key=f"objective:{session.id}:unsafe_tool_invocation_triggered:31",
        trigger_event_index=31,
    )
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key="security_boundary_crossed",
        occurred_at=now,
        idempotency_key=f"objective:{session.id}:security_boundary_crossed:32",
        trigger_event_index=32,
    )
    db_session.flush()

    result = process_pending_objective_completed_once(
        outbox_repo=SQLAlchemyOutboxSessionObjectiveCompleted(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
    )
    db_session.flush()

    assert result.claimed_count == 2
    assert result.succeeded_count == 2
    assert result.failed_count == 0
    assert result.retried_count == 0

    objective_rows = (
        db_session.execute(
            select(SessionObjectiveModel)
            .where(SessionObjectiveModel.session_id == session.id)
            .order_by(SessionObjectiveModel.sort_order.asc())
        )
        .scalars()
        .all()
    )
    assert len(objective_rows) == 3
    assert objective_rows[0].objective_key == "unsafe_tool_invocation_triggered"
    assert objective_rows[0].status == "complete"
    assert objective_rows[1].objective_key == "security_boundary_crossed"
    assert objective_rows[1].status == "complete"
    assert objective_rows[2].objective_key == "critical_file_deleted"
    assert objective_rows[2].status == "pending"
    assert objective_rows[2].completed_at is None


def test_objective_projector_marks_lab3_objective_pending_to_complete(
    db_session: Session,
) -> None:
    session = _seed_session(
        db_session,
        lab_id=UUID_LAB_3,
        lab_version_id=UUID_LAB_3_VERSION,
    )
    objective_key = "malicious_vendor_memory_written"
    occurred_at = datetime(2026, 4, 21, 17, 30, 0, tzinfo=timezone.utc)

    _seed_session_objective(
        db_session,
        session_id=session.id,
        objective_key=objective_key,
        label="Malicious Vendor Memory Written",
        sort_order=0,
    )
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key=objective_key,
        occurred_at=occurred_at,
        idempotency_key=f"objective:{session.id}:{objective_key}:41",
        trigger_event_index=41,
        lab_id=UUID_LAB_3,
        lab_version_id=UUID_LAB_3_VERSION,
    )
    db_session.flush()

    result = process_pending_objective_completed_once(
        outbox_repo=SQLAlchemyOutboxSessionObjectiveCompleted(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
    )
    db_session.flush()

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert result.retried_count == 0

    objective_row = (
        db_session.execute(
            select(SessionObjectiveModel).where(
                SessionObjectiveModel.session_id == session.id,
                SessionObjectiveModel.objective_key == objective_key,
            )
        )
        .scalars()
        .one()
    )
    assert objective_row.status == "complete"
    assert objective_row.completed_at == occurred_at


def test_objective_projector_lab3_completion_persists_after_reload(
    db_session: Session,
) -> None:
    session = _seed_session(
        db_session,
        lab_id=UUID_LAB_3,
        lab_version_id=UUID_LAB_3_VERSION,
    )
    objective_key = "payment_routed_to_attacker_account"
    occurred_at = datetime(2026, 4, 21, 18, 0, 0, tzinfo=timezone.utc)

    _seed_session_objective(
        db_session,
        session_id=session.id,
        objective_key=objective_key,
        label="Payment Routed To Attacker Account",
        sort_order=0,
    )
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key=objective_key,
        occurred_at=occurred_at,
        idempotency_key=f"objective:{session.id}:{objective_key}:42",
        trigger_event_index=42,
        lab_id=UUID_LAB_3,
        lab_version_id=UUID_LAB_3_VERSION,
    )
    db_session.flush()

    process_pending_objective_completed_once(
        outbox_repo=SQLAlchemyOutboxSessionObjectiveCompleted(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
    )
    db_session.commit()
    db_session.expire_all()

    reloaded_row = (
        db_session.execute(
            select(SessionObjectiveModel).where(
                SessionObjectiveModel.session_id == session.id,
                SessionObjectiveModel.objective_key == objective_key,
            )
        )
        .scalars()
        .one()
    )
    assert reloaded_row.status == "complete"
    assert reloaded_row.completed_at == occurred_at


def test_objective_projector_lab3_duplicate_replay_second_pass_no_op(
    db_session: Session,
) -> None:
    session = _seed_session(
        db_session,
        lab_id=UUID_LAB_3,
        lab_version_id=UUID_LAB_3_VERSION,
    )
    objective_key = "poisoned_memory_retrieved_for_invoice"
    first_occurred_at = datetime(2026, 4, 21, 18, 10, 0, tzinfo=timezone.utc)
    replay_occurred_at = datetime(2026, 4, 21, 18, 15, 0, tzinfo=timezone.utc)

    _seed_session_objective(
        db_session,
        session_id=session.id,
        objective_key=objective_key,
        label="Poisoned Memory Retrieved For Invoice",
        sort_order=0,
    )
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key=objective_key,
        occurred_at=first_occurred_at,
        idempotency_key=f"objective:{session.id}:{objective_key}:51",
        trigger_event_index=51,
        lab_id=UUID_LAB_3,
        lab_version_id=UUID_LAB_3_VERSION,
    )
    db_session.flush()

    first_result = process_pending_objective_completed_once(
        outbox_repo=SQLAlchemyOutboxSessionObjectiveCompleted(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
    )
    db_session.flush()

    assert first_result.claimed_count == 1
    assert first_result.succeeded_count == 1
    assert first_result.failed_count == 0
    assert first_result.retried_count == 0

    row_after_first_pass = (
        db_session.execute(
            select(SessionObjectiveModel).where(
                SessionObjectiveModel.session_id == session.id,
                SessionObjectiveModel.objective_key == objective_key,
            )
        )
        .scalars()
        .one()
    )
    assert row_after_first_pass.status == "complete"
    assert row_after_first_pass.completed_at == first_occurred_at
    first_updated_at = row_after_first_pass.updated_at

    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key=objective_key,
        occurred_at=replay_occurred_at,
        idempotency_key=f"objective:{session.id}:{objective_key}:52",
        trigger_event_index=52,
        lab_id=UUID_LAB_3,
        lab_version_id=UUID_LAB_3_VERSION,
    )
    db_session.flush()

    second_result = process_pending_objective_completed_once(
        outbox_repo=SQLAlchemyOutboxSessionObjectiveCompleted(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
    )
    db_session.flush()

    assert second_result.claimed_count == 1
    assert second_result.succeeded_count == 1
    assert second_result.failed_count == 0
    assert second_result.retried_count == 0

    row_after_replay = (
        db_session.execute(
            select(SessionObjectiveModel).where(
                SessionObjectiveModel.session_id == session.id,
                SessionObjectiveModel.objective_key == objective_key,
            )
        )
        .scalars()
        .one()
    )
    assert row_after_replay.status == "complete"
    assert row_after_replay.completed_at == first_occurred_at
    assert row_after_replay.updated_at == first_updated_at
