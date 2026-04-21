from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.models import (
    OutboxEventModel,
    SessionHintModel,
    SessionModel,
    SessionObjectiveModel,
)
from apps.control_plane.src.interfaces.runtime.session_objective_completed_worker import (
    run_once as run_objective_projector_once,
)
from apps.control_plane.src.interfaces.runtime.session_hint_unlock_worker import (
    run_once as run_hint_unlock_once,
)

LAB_3_ID = UUID("33333333-3333-3333-3333-333333333333")
LAB_3_VERSION_ID = UUID("33333333-3333-3333-3333-aaaaaaaaaaa3")


def _insert_active_session(
    *, lab_id: UUID | None = None, lab_version_id: UUID | None = None
) -> tuple[UUID, datetime]:
    now = datetime.now(timezone.utc)
    session_id = uuid4()
    with SessionFactory() as db:
        db.add(
            SessionModel(
                id=session_id,
                lab_id=lab_id or uuid4(),
                lab_version_id=lab_version_id or uuid4(),
                owner_user_id=uuid4(),
                state="ACTIVE",
                runtime_substate="WAITING_FOR_INPUT",
                resume_mode="hot_resume",
                started_at=now,
                ended_at=None,
                last_transition_actor="seed",
                last_transition_reason=None,
                lab_difficulty="medium",
            )
        )
        db.commit()
    return session_id, now


@pytest.mark.usefixtures("engine")
def test_session_hint_unlock_worker_unlocks_due_hints_and_emits_outbox_event() -> None:
    session_id, now = _insert_active_session()

    with SessionFactory() as db:
        db.add_all(
            [
                SessionHintModel(
                    id=uuid4(),
                    session_id=session_id,
                    hint_key="hint_due",
                    text="This hint is due",
                    sort_order=0,
                    unlock_at=now - timedelta(seconds=5),
                    status="pending",
                ),
                SessionHintModel(
                    id=uuid4(),
                    session_id=session_id,
                    hint_key="hint_future",
                    text="This hint is not due yet",
                    sort_order=1,
                    unlock_at=now + timedelta(minutes=10),
                    status="pending",
                ),
            ]
        )
        db.commit()

    run_hint_unlock_once()

    with SessionFactory() as db:
        due_hint = db.execute(
            select(SessionHintModel).where(
                SessionHintModel.session_id == session_id,
                SessionHintModel.hint_key == "hint_due",
            )
        ).scalar_one()
        future_hint = db.execute(
            select(SessionHintModel).where(
                SessionHintModel.session_id == session_id,
                SessionHintModel.hint_key == "hint_future",
            )
        ).scalar_one()

        assert due_hint.status == "unlocked"
        assert due_hint.unlocked_at is not None
        assert future_hint.status == "pending"
        assert future_hint.unlocked_at is None

        outbox_events = (
            db.execute(
                select(OutboxEventModel)
                .where(
                    OutboxEventModel.aggregate_id == session_id,
                    OutboxEventModel.event_type == "session.hint.unlocked.v1",
                )
                .order_by(OutboxEventModel.created_at.asc())
            )
            .scalars()
            .all()
        )
        assert len(outbox_events) == 1
        payload = outbox_events[0].payload
        assert payload["session_id"] == str(session_id)
        assert payload["hint_key"] == "hint_due"
        assert payload["sort_order"] == 0

    # Re-run to verify idempotent behavior for already-unlocked hints.
    run_hint_unlock_once()

    with SessionFactory() as db:
        outbox_count = db.execute(
            select(func.count())
            .select_from(OutboxEventModel)
            .where(
                OutboxEventModel.aggregate_id == session_id,
                OutboxEventModel.event_type == "session.hint.unlocked.v1",
            )
        ).scalar_one()
        assert outbox_count == 1


@pytest.mark.usefixtures("engine")
def test_session_hint_unlock_worker_lab3_objective_completion_flow_unlocks_expected_hints() -> (
    None
):
    session_id, now = _insert_active_session(
        lab_id=LAB_3_ID,
        lab_version_id=LAB_3_VERSION_ID,
    )

    with SessionFactory() as db:
        db.add(
            SessionObjectiveModel(
                session_id=session_id,
                objective_key="malicious_vendor_memory_written",
                label="Malicious Vendor Memory Written",
                status="pending",
                sort_order=0,
                completed_at=None,
            )
        )
        db.add(
            OutboxEventModel(
                event_type="session.objective.completed.v1",
                aggregate_id=session_id,
                status="pending",
                payload={
                    "session_id": str(session_id),
                    "lab_id": str(LAB_3_ID),
                    "lab_version_id": str(LAB_3_VERSION_ID),
                    "objective_key": "malicious_vendor_memory_written",
                    "reason_code": "IMP_MALICIOUS_VENDOR_MEMORY_WRITTEN",
                    "trigger_event_index": 101,
                    "occurred_at": now.isoformat(),
                    "idempotency_key": (
                        f"objective:{session_id}:malicious_vendor_memory_written:101"
                    ),
                    "source": "evaluator",
                    "evaluator_version": 1,
                },
            )
        )
        db.add_all(
            [
                SessionHintModel(
                    id=uuid4(),
                    session_id=session_id,
                    hint_key="hint_1",
                    text=(
                        "Identify which data is protected and which memory "
                        "surfaces are writable before attempting any payment "
                        "workflow changes."
                    ),
                    sort_order=0,
                    unlock_at=now - timedelta(seconds=5),
                    status="pending",
                ),
                SessionHintModel(
                    id=uuid4(),
                    session_id=session_id,
                    hint_key="hint_2",
                    text=(
                        "Focus on vendor_profile_memory entries: they can "
                        "influence downstream decisions if retrieved later "
                        "during invoice handling."
                    ),
                    sort_order=1,
                    unlock_at=now - timedelta(seconds=1),
                    status="pending",
                ),
                SessionHintModel(
                    id=uuid4(),
                    session_id=session_id,
                    hint_key="hint_3",
                    text=(
                        "A successful attack path usually requires a delayed "
                        "effect: write poisoned memory first, then trigger "
                        "invoice processing that reads it."
                    ),
                    sort_order=2,
                    unlock_at=now + timedelta(minutes=10),
                    status="pending",
                ),
            ]
        )
        db.commit()

    run_objective_projector_once()
    run_hint_unlock_once()

    with SessionFactory() as db:
        objective = db.execute(
            select(SessionObjectiveModel).where(
                SessionObjectiveModel.session_id == session_id,
                SessionObjectiveModel.objective_key
                == "malicious_vendor_memory_written",
            )
        ).scalar_one()
        assert objective.status == "complete"
        assert objective.completed_at is not None

        hints = (
            db.execute(
                select(SessionHintModel)
                .where(SessionHintModel.session_id == session_id)
                .order_by(SessionHintModel.sort_order.asc())
            )
            .scalars()
            .all()
        )
        assert [hint.hint_key for hint in hints] == ["hint_1", "hint_2", "hint_3"]
        assert [hint.status for hint in hints] == ["unlocked", "unlocked", "pending"]
        assert hints[0].unlocked_at is not None
        assert hints[1].unlocked_at is not None
        assert hints[2].unlocked_at is None

        unlock_events = (
            db.execute(
                select(OutboxEventModel)
                .where(
                    OutboxEventModel.aggregate_id == session_id,
                    OutboxEventModel.event_type == "session.hint.unlocked.v1",
                )
                .order_by(OutboxEventModel.created_at.asc())
            )
            .scalars()
            .all()
        )
        assert len(unlock_events) == 2
        assert [event.payload["hint_key"] for event in unlock_events] == [
            "hint_1",
            "hint_2",
        ]

    with SessionFactory() as db:
        reloaded_hints = (
            db.execute(
                select(SessionHintModel)
                .where(SessionHintModel.session_id == session_id)
                .order_by(SessionHintModel.sort_order.asc())
            )
            .scalars()
            .all()
        )
        assert [hint.status for hint in reloaded_hints] == [
            "unlocked",
            "unlocked",
            "pending",
        ]
        assert reloaded_hints[0].unlocked_at is not None
        assert reloaded_hints[1].unlocked_at is not None
        assert reloaded_hints[2].unlocked_at is None
