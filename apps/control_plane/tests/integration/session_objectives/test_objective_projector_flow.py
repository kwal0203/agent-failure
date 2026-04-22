from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.control_plane.src.application.session_objectives.service import (
    process_pending_objective_completed_once,
)
from apps.control_plane.src.infrastructure.persistence.models import (
    LabObjectivesModel,
    OutboxEventModel,
    SessionModel,
    SessionObjectiveModel,
)
from apps.control_plane.src.infrastructure.persistence.outbox import SQLAlchemyOutbox
from apps.control_plane.src.infrastructure.persistence.outbox_session_objective_completed import (
    SQLAlchemyOutboxSessionObjectiveCompleted,
)
from apps.control_plane.src.infrastructure.persistence.session_objectives_repository import (
    SQLAlchemyLabObjectiveTemplateRepository,
    SQLAlchemySessionObjectiveWriterRepository,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionRepository,
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


def _seed_lab_objective_template(
    db_session: Session,
    *,
    lab_version_id,
    objective_key: str,
    label: str,
    sort_order: int,
) -> None:
    db_session.add(
        LabObjectivesModel(
            lab_version_id=lab_version_id,
            objective_key=objective_key,
            label=label,
            sort_order=sort_order,
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
        event_outbox_repo=SQLAlchemyOutbox(db=db_session),
        template_reader=SQLAlchemyLabObjectiveTemplateRepository(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
        completion_writer=SQLAlchemySessionRepository(db=db_session),
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
        event_outbox_repo=SQLAlchemyOutbox(db=db_session),
        template_reader=SQLAlchemyLabObjectiveTemplateRepository(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
        completion_writer=SQLAlchemySessionRepository(db=db_session),
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
        event_outbox_repo=SQLAlchemyOutbox(db=db_session),
        template_reader=SQLAlchemyLabObjectiveTemplateRepository(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
        completion_writer=SQLAlchemySessionRepository(db=db_session),
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
        event_outbox_repo=SQLAlchemyOutbox(db=db_session),
        template_reader=SQLAlchemyLabObjectiveTemplateRepository(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
        completion_writer=SQLAlchemySessionRepository(db=db_session),
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
        event_outbox_repo=SQLAlchemyOutbox(db=db_session),
        template_reader=SQLAlchemyLabObjectiveTemplateRepository(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
        completion_writer=SQLAlchemySessionRepository(db=db_session),
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
        event_outbox_repo=SQLAlchemyOutbox(db=db_session),
        template_reader=SQLAlchemyLabObjectiveTemplateRepository(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
        completion_writer=SQLAlchemySessionRepository(db=db_session),
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
        event_outbox_repo=SQLAlchemyOutbox(db=db_session),
        template_reader=SQLAlchemyLabObjectiveTemplateRepository(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
        completion_writer=SQLAlchemySessionRepository(db=db_session),
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


def test_objective_projector_marks_session_completed_success_when_all_required_objectives_complete(
    db_session: Session,
) -> None:
    session = _seed_session(db_session)
    _seed_lab_objective_template(
        db_session,
        lab_version_id=session.lab_version_id,
        objective_key="unsafe_tool_invocation_triggered",
        label="Unsafe Tool Invocation Triggered",
        sort_order=0,
    )
    _seed_lab_objective_template(
        db_session,
        lab_version_id=session.lab_version_id,
        objective_key="security_boundary_crossed",
        label="Security Boundary Crossed",
        sort_order=1,
    )
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
    completed_at = datetime(2026, 4, 22, 7, 15, 0, tzinfo=timezone.utc)
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key="unsafe_tool_invocation_triggered",
        occurred_at=completed_at,
        idempotency_key=f"objective:{session.id}:unsafe_tool_invocation_triggered:61",
        trigger_event_index=61,
    )
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key="security_boundary_crossed",
        occurred_at=completed_at,
        idempotency_key=f"objective:{session.id}:security_boundary_crossed:62",
        trigger_event_index=62,
    )
    db_session.flush()

    result = process_pending_objective_completed_once(
        outbox_repo=SQLAlchemyOutboxSessionObjectiveCompleted(db=db_session),
        event_outbox_repo=SQLAlchemyOutbox(db=db_session),
        template_reader=SQLAlchemyLabObjectiveTemplateRepository(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
        completion_writer=SQLAlchemySessionRepository(db=db_session),
    )
    db_session.flush()

    assert result.claimed_count == 2
    assert result.succeeded_count == 2

    db_session.expire_all()
    session_row = db_session.get(SessionModel, session.id)
    assert session_row is not None
    assert session_row.completion_status == "completed_success"
    assert session_row.completion_reason_code == "ALL_REQUIRED_OBJECTIVES_COMPLETED"
    assert session_row.completed_at == completed_at


def test_objective_projector_emits_session_completed_event_when_all_required_complete(
    db_session: Session,
) -> None:
    session = _seed_session(db_session)
    _seed_lab_objective_template(
        db_session,
        lab_version_id=session.lab_version_id,
        objective_key="unsafe_tool_invocation_triggered",
        label="Unsafe Tool Invocation Triggered",
        sort_order=0,
    )
    _seed_lab_objective_template(
        db_session,
        lab_version_id=session.lab_version_id,
        objective_key="security_boundary_crossed",
        label="Security Boundary Crossed",
        sort_order=1,
    )
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
    completed_at = datetime(2026, 4, 22, 8, 30, 0, tzinfo=timezone.utc)
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key="unsafe_tool_invocation_triggered",
        occurred_at=completed_at,
        idempotency_key=f"objective:{session.id}:unsafe_tool_invocation_triggered:81",
        trigger_event_index=81,
    )
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key="security_boundary_crossed",
        occurred_at=completed_at,
        idempotency_key=f"objective:{session.id}:security_boundary_crossed:82",
        trigger_event_index=82,
    )
    db_session.flush()

    result = process_pending_objective_completed_once(
        outbox_repo=SQLAlchemyOutboxSessionObjectiveCompleted(db=db_session),
        event_outbox_repo=SQLAlchemyOutbox(db=db_session),
        template_reader=SQLAlchemyLabObjectiveTemplateRepository(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
        completion_writer=SQLAlchemySessionRepository(db=db_session),
    )
    db_session.flush()

    assert result.succeeded_count == 2

    completed_events = (
        db_session.execute(
            select(OutboxEventModel)
            .where(
                OutboxEventModel.event_type == "session.completed.v1",
                OutboxEventModel.aggregate_id == session.id,
            )
            .order_by(OutboxEventModel.created_at.asc())
        )
        .scalars()
        .all()
    )
    assert len(completed_events) == 1
    payload = completed_events[0].payload
    assert payload["session_id"] == str(session.id)
    assert payload["lab_id"] == str(session.lab_id)
    assert payload["lab_version_id"] == str(session.lab_version_id)
    assert payload["outcome"] == "completed_success"
    assert payload["completion_reason_code"] == "ALL_REQUIRED_OBJECTIVES_COMPLETED"
    assert payload["trigger_event_index"] == 82
    occurred_at = datetime.fromisoformat(
        str(payload["occurred_at"]).replace("Z", "+00:00")
    )
    assert occurred_at == completed_at
    assert (
        payload["idempotency_key"]
        == f"session_completed:{session.id}:completed_success:"
        "all_required_objectives_completed:82"
    )


def test_objective_projector_does_not_mark_session_completed_when_any_required_objective_pending(
    db_session: Session,
) -> None:
    session = _seed_session(db_session)
    _seed_lab_objective_template(
        db_session,
        lab_version_id=session.lab_version_id,
        objective_key="unsafe_tool_invocation_triggered",
        label="Unsafe Tool Invocation Triggered",
        sort_order=0,
    )
    _seed_lab_objective_template(
        db_session,
        lab_version_id=session.lab_version_id,
        objective_key="security_boundary_crossed",
        label="Security Boundary Crossed",
        sort_order=1,
    )
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
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key="unsafe_tool_invocation_triggered",
        occurred_at=datetime(2026, 4, 22, 7, 30, 0, tzinfo=timezone.utc),
        idempotency_key=f"objective:{session.id}:unsafe_tool_invocation_triggered:63",
        trigger_event_index=63,
    )
    db_session.flush()

    result = process_pending_objective_completed_once(
        outbox_repo=SQLAlchemyOutboxSessionObjectiveCompleted(db=db_session),
        event_outbox_repo=SQLAlchemyOutbox(db=db_session),
        template_reader=SQLAlchemyLabObjectiveTemplateRepository(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
        completion_writer=SQLAlchemySessionRepository(db=db_session),
    )
    db_session.flush()

    assert result.claimed_count == 1
    assert result.succeeded_count == 1

    db_session.expire_all()
    session_row = db_session.get(SessionModel, session.id)
    assert session_row is not None
    assert session_row.completion_status == "in_progress"
    assert session_row.completion_reason_code is None
    assert session_row.completed_at is None


def test_objective_projector_replay_does_not_overwrite_terminal_completion(
    db_session: Session,
) -> None:
    session = _seed_session(db_session)
    _seed_lab_objective_template(
        db_session,
        lab_version_id=session.lab_version_id,
        objective_key="unsafe_tool_invocation_triggered",
        label="Unsafe Tool Invocation Triggered",
        sort_order=0,
    )
    _seed_lab_objective_template(
        db_session,
        lab_version_id=session.lab_version_id,
        objective_key="security_boundary_crossed",
        label="Security Boundary Crossed",
        sort_order=1,
    )
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
    first_completed_at = datetime(2026, 4, 22, 8, 0, 0, tzinfo=timezone.utc)
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key="unsafe_tool_invocation_triggered",
        occurred_at=first_completed_at,
        idempotency_key=f"objective:{session.id}:unsafe_tool_invocation_triggered:71",
        trigger_event_index=71,
    )
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key="security_boundary_crossed",
        occurred_at=first_completed_at,
        idempotency_key=f"objective:{session.id}:security_boundary_crossed:72",
        trigger_event_index=72,
    )
    db_session.flush()

    first_result = process_pending_objective_completed_once(
        outbox_repo=SQLAlchemyOutboxSessionObjectiveCompleted(db=db_session),
        event_outbox_repo=SQLAlchemyOutbox(db=db_session),
        template_reader=SQLAlchemyLabObjectiveTemplateRepository(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
        completion_writer=SQLAlchemySessionRepository(db=db_session),
    )
    db_session.flush()
    assert first_result.succeeded_count == 2

    db_session.expire_all()
    first_session_row = db_session.get(SessionModel, session.id)
    assert first_session_row is not None
    assert first_session_row.completion_status == "completed_success"
    assert first_session_row.completed_at == first_completed_at

    replay_completed_at = datetime(2026, 4, 22, 8, 5, 0, tzinfo=timezone.utc)
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key="security_boundary_crossed",
        occurred_at=replay_completed_at,
        idempotency_key=f"objective:{session.id}:security_boundary_crossed:73",
        trigger_event_index=73,
    )
    db_session.flush()

    second_result = process_pending_objective_completed_once(
        outbox_repo=SQLAlchemyOutboxSessionObjectiveCompleted(db=db_session),
        event_outbox_repo=SQLAlchemyOutbox(db=db_session),
        template_reader=SQLAlchemyLabObjectiveTemplateRepository(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
        completion_writer=SQLAlchemySessionRepository(db=db_session),
    )
    db_session.flush()
    assert second_result.succeeded_count == 1

    db_session.expire_all()
    second_session_row = db_session.get(SessionModel, session.id)
    assert second_session_row is not None
    assert second_session_row.completion_status == "completed_success"
    assert (
        second_session_row.completion_reason_code == "ALL_REQUIRED_OBJECTIVES_COMPLETED"
    )
    assert second_session_row.completed_at == first_completed_at


def test_objective_projector_replay_does_not_emit_duplicate_session_completed_event(
    db_session: Session,
) -> None:
    session = _seed_session(db_session)
    _seed_lab_objective_template(
        db_session,
        lab_version_id=session.lab_version_id,
        objective_key="unsafe_tool_invocation_triggered",
        label="Unsafe Tool Invocation Triggered",
        sort_order=0,
    )
    _seed_session_objective(
        db_session,
        session_id=session.id,
        objective_key="unsafe_tool_invocation_triggered",
        label="Unsafe Tool Invocation Triggered",
        sort_order=0,
    )
    first_completed_at = datetime(2026, 4, 22, 8, 40, 0, tzinfo=timezone.utc)
    replay_completed_at = datetime(2026, 4, 22, 8, 41, 0, tzinfo=timezone.utc)
    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key="unsafe_tool_invocation_triggered",
        occurred_at=first_completed_at,
        idempotency_key=f"objective:{session.id}:unsafe_tool_invocation_triggered:91",
        trigger_event_index=91,
    )
    db_session.flush()

    first_result = process_pending_objective_completed_once(
        outbox_repo=SQLAlchemyOutboxSessionObjectiveCompleted(db=db_session),
        event_outbox_repo=SQLAlchemyOutbox(db=db_session),
        template_reader=SQLAlchemyLabObjectiveTemplateRepository(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
        completion_writer=SQLAlchemySessionRepository(db=db_session),
    )
    assert first_result.succeeded_count == 1

    _seed_objective_completed_event(
        db_session,
        session_id=session.id,
        objective_key="unsafe_tool_invocation_triggered",
        occurred_at=replay_completed_at,
        idempotency_key=f"objective:{session.id}:unsafe_tool_invocation_triggered:92",
        trigger_event_index=92,
    )
    db_session.flush()

    second_result = process_pending_objective_completed_once(
        outbox_repo=SQLAlchemyOutboxSessionObjectiveCompleted(db=db_session),
        event_outbox_repo=SQLAlchemyOutbox(db=db_session),
        template_reader=SQLAlchemyLabObjectiveTemplateRepository(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
        completion_writer=SQLAlchemySessionRepository(db=db_session),
    )
    assert second_result.succeeded_count == 1
    db_session.flush()

    completed_events = (
        db_session.execute(
            select(OutboxEventModel)
            .where(
                OutboxEventModel.event_type == "session.completed.v1",
                OutboxEventModel.aggregate_id == session.id,
            )
            .order_by(OutboxEventModel.created_at.asc())
        )
        .scalars()
        .all()
    )
    assert len(completed_events) == 1
    payload = completed_events[0].payload
    assert payload["trigger_event_index"] == 91
    assert (
        payload["idempotency_key"]
        == f"session_completed:{session.id}:completed_success:"
        "all_required_objectives_completed:91"
    )
