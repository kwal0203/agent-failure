from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select

from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.models import (
    OutboxEventModel,
    SessionFeedbackModel,
    SessionModel,
)
from apps.control_plane.src.interfaces.runtime.session_feedback_created_worker import (
    run_once as run_session_feedback_created_once,
)


def _seed_active_session() -> tuple[UUID, datetime]:
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
                completion_status="in_progress",
                completed_at=None,
                completion_reason_code=None,
                resume_mode="hot_resume",
                started_at=now,
                ended_at=None,
                last_transition_actor="seed",
                last_transition_reason=None,
            )
        )
        db.commit()
    return session_id, now


def _seed_feedback_created_outbox_event(
    *,
    session_id: UUID,
    created_at: datetime,
    outbox_status: str = "pending",
) -> None:
    with SessionFactory() as db:
        db.add(
            OutboxEventModel(
                event_type="session.feedback.created.v1",
                aggregate_id=session_id,
                status=outbox_status,
                payload={
                    "session_id": str(session_id),
                    "lab_id": str(uuid4()),
                    "lab_version_id": str(uuid4()),
                    "feedback_key": "lab1_benign_email_not_progressing",
                    "reason_code": "PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS",
                    "message": (
                        "This email was benign. It did not move the attack chain forward."
                    ),
                    "severity": "info",
                    "trigger_event_index": 11,
                    "created_at": created_at.isoformat(),
                    "idempotency_key": f"feedback:v1:{session_id}:11",
                },
            )
        )
        db.commit()


def _count_unread_feedback(*, session_id: UUID) -> int:
    with SessionFactory() as db:
        return int(
            db.execute(
                select(func.count())
                .select_from(SessionFeedbackModel)
                .where(
                    SessionFeedbackModel.session_id == session_id,
                    SessionFeedbackModel.seen_at.is_(None),
                )
            ).scalar_one()
        )


@pytest.mark.usefixtures("engine")
def test_session_feedback_created_worker_projects_feedback_row_and_unread() -> None:
    session_id, created_at = _seed_active_session()
    _seed_feedback_created_outbox_event(
        session_id=session_id,
        created_at=created_at,
    )

    run_session_feedback_created_once()

    with SessionFactory() as db:
        feedback_rows = (
            db.execute(
                select(SessionFeedbackModel).where(
                    SessionFeedbackModel.session_id == session_id
                )
            )
            .scalars()
            .all()
        )
        outbox = db.execute(
            select(OutboxEventModel).where(
                OutboxEventModel.aggregate_id == session_id,
                OutboxEventModel.event_type == "session.feedback.created.v1",
            )
        ).scalar_one()

        assert len(feedback_rows) == 1
        assert feedback_rows[0].feedback_key == "lab1_benign_email_not_progressing"
        assert feedback_rows[0].reason_code == "PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS"
        assert feedback_rows[0].severity == "info"
        assert feedback_rows[0].seen_at is None
        assert outbox.status == "processed"
        assert outbox.processed_at is not None

    assert _count_unread_feedback(session_id=session_id) == 1


@pytest.mark.usefixtures("engine")
def test_session_feedback_created_worker_replay_is_idempotent() -> None:
    session_id, created_at = _seed_active_session()
    _seed_feedback_created_outbox_event(
        session_id=session_id,
        created_at=created_at,
    )

    run_session_feedback_created_once()

    with SessionFactory() as db:
        row_count_before = int(
            db.execute(
                select(func.count())
                .select_from(SessionFeedbackModel)
                .where(SessionFeedbackModel.session_id == session_id)
            ).scalar_one()
        )
        unread_before = int(
            db.execute(
                select(func.count())
                .select_from(SessionFeedbackModel)
                .where(
                    SessionFeedbackModel.session_id == session_id,
                    SessionFeedbackModel.seen_at.is_(None),
                )
            ).scalar_one()
        )
        outbox = db.execute(
            select(OutboxEventModel).where(
                OutboxEventModel.aggregate_id == session_id,
                OutboxEventModel.event_type == "session.feedback.created.v1",
            )
        ).scalar_one()
        outbox.status = "pending"
        outbox.processed_at = None
        db.commit()

    run_session_feedback_created_once()

    with SessionFactory() as db:
        row_count_after = int(
            db.execute(
                select(func.count())
                .select_from(SessionFeedbackModel)
                .where(SessionFeedbackModel.session_id == session_id)
            ).scalar_one()
        )
        unread_after = int(
            db.execute(
                select(func.count())
                .select_from(SessionFeedbackModel)
                .where(
                    SessionFeedbackModel.session_id == session_id,
                    SessionFeedbackModel.seen_at.is_(None),
                )
            ).scalar_one()
        )
        replayed_outbox = db.execute(
            select(OutboxEventModel).where(
                OutboxEventModel.aggregate_id == session_id,
                OutboxEventModel.event_type == "session.feedback.created.v1",
            )
        ).scalar_one()

        assert row_count_before == 1
        assert row_count_after == 1
        assert unread_before == 1
        assert unread_after == 1
        assert replayed_outbox.status == "processed"
        assert replayed_outbox.processed_at is not None
