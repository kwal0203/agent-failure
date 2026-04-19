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
)
from apps.control_plane.src.interfaces.runtime.session_hint_unlock_worker import (
    run_once,
)


def _insert_active_session() -> tuple[UUID, datetime]:
    now = datetime.now(timezone.utc)
    session_id = uuid4()
    with SessionFactory() as db:
        db.add(
            SessionModel(
                id=session_id,
                lab_id=uuid4(),
                lab_version_id=uuid4(),
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

    run_once()

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
    run_once()

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
