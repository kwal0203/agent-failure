from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.models import (
    OutboxEventModel,
    SessionModel,
)
from apps.control_plane.src.interfaces.runtime.session_completed_worker import (
    run_once as run_session_completed_once,
)


def _seed_session(*, completion_status: str = "in_progress") -> tuple[UUID, datetime]:
    session_id = uuid4()
    now = datetime.now(timezone.utc)
    with SessionFactory() as db:
        db.add(
            SessionModel(
                id=session_id,
                lab_id=uuid4(),
                lab_version_id=uuid4(),
                owner_user_id=uuid4(),
                state="ACTIVE",
                runtime_substate="WAITING_FOR_INPUT",
                completion_status=completion_status,
                completed_at=None if completion_status == "in_progress" else now,
                completion_reason_code=(
                    None
                    if completion_status == "in_progress"
                    else "ALL_REQUIRED_OBJECTIVES_COMPLETED"
                ),
                resume_mode="hot_resume",
                started_at=now,
                ended_at=None,
                last_transition_actor="seed",
                last_transition_reason=None,
            )
        )
        db.commit()
    return session_id, now


def _seed_session_completed_outbox_event(
    *,
    session_id: UUID,
    occurred_at: datetime,
    outbox_status: str = "pending",
) -> None:
    with SessionFactory() as db:
        db.add(
            OutboxEventModel(
                event_type="session.completed.v1",
                aggregate_id=session_id,
                status=outbox_status,
                payload={
                    "session_id": str(session_id),
                    "lab_id": str(uuid4()),
                    "lab_version_id": str(uuid4()),
                    "outcome": "completed_success",
                    "completion_reason_code": "ALL_REQUIRED_OBJECTIVES_COMPLETED",
                    "trigger_event_index": 99,
                    "occurred_at": occurred_at.isoformat(),
                    "idempotency_key": f"session_completed:{session_id}:99",
                },
            )
        )
        db.commit()


@pytest.mark.usefixtures("engine")
def test_session_completed_worker_projects_completion_fields() -> None:
    session_id_raw, occurred_at = _seed_session(completion_status="in_progress")
    _seed_session_completed_outbox_event(
        session_id=session_id_raw,
        occurred_at=occurred_at,
    )

    run_session_completed_once()

    with SessionFactory() as db:
        session = db.execute(
            select(SessionModel).where(SessionModel.id == session_id_raw)
        ).scalar_one()
        outbox = db.execute(
            select(OutboxEventModel).where(
                OutboxEventModel.aggregate_id == session_id_raw,
                OutboxEventModel.event_type == "session.completed.v1",
            )
        ).scalar_one()

        assert session.completion_status == "completed_success"
        assert session.completed_at == occurred_at
        assert session.completion_reason_code == "ALL_REQUIRED_OBJECTIVES_COMPLETED"
        assert outbox.status == "processed"
        assert outbox.processed_at is not None


@pytest.mark.usefixtures("engine")
def test_session_completed_worker_duplicate_replay_is_no_op() -> None:
    session_id_raw, occurred_at = _seed_session(completion_status="in_progress")
    _seed_session_completed_outbox_event(
        session_id=session_id_raw,
        occurred_at=occurred_at,
    )

    run_session_completed_once()

    with SessionFactory() as db:
        session_before = db.execute(
            select(SessionModel).where(SessionModel.id == session_id_raw)
        ).scalar_one()
        first_completed_at = session_before.completed_at

        outbox = db.execute(
            select(OutboxEventModel).where(
                OutboxEventModel.aggregate_id == session_id_raw,
                OutboxEventModel.event_type == "session.completed.v1",
            )
        ).scalar_one()
        outbox.status = "pending"
        outbox.processed_at = None
        db.commit()

    run_session_completed_once()

    with SessionFactory() as db:
        session_after = db.execute(
            select(SessionModel).where(SessionModel.id == session_id_raw)
        ).scalar_one()
        replayed_outbox = db.execute(
            select(OutboxEventModel).where(
                OutboxEventModel.aggregate_id == session_id_raw,
                OutboxEventModel.event_type == "session.completed.v1",
            )
        ).scalar_one()

        assert session_after.completion_status == "completed_success"
        assert session_after.completed_at == first_completed_at
        assert (
            session_after.completion_reason_code == "ALL_REQUIRED_OBJECTIVES_COMPLETED"
        )
        assert replayed_outbox.status == "processed"
        assert replayed_outbox.processed_at is not None
