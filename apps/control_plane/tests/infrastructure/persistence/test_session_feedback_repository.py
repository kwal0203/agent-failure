from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from apps.control_plane.src.application.session_feedback.types import (
    SessionFeedbackCreateInput,
)
from apps.control_plane.src.infrastructure.persistence.models import SessionModel
from apps.control_plane.src.infrastructure.persistence.session_feedback_repository import (
    SQLAlchemySessionFeedbackRepository,
)


def _insert_session(db_session: Session) -> SessionModel:
    session = SessionModel(
        id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        owner_user_id=uuid4(),
        state="ACTIVE",
        runtime_substate="WAITING_FOR_INPUT",
        resume_mode="hot_resume",
        started_at=datetime.now(timezone.utc),
        ended_at=None,
        last_transition_actor="seed",
        last_transition_reason=None,
        lab_difficulty="medium",
    )
    db_session.add(session)
    db_session.flush()
    return session


def test_insert_feedback_if_absent_is_idempotent(db_session: Session) -> None:
    repo = SQLAlchemySessionFeedbackRepository(db=db_session)
    session = _insert_session(db_session)
    now = datetime.now(timezone.utc)
    input = SessionFeedbackCreateInput(
        session_id=session.id,
        feedback_key="lab1_benign_email_no_progress",
        reason_code="BENIGN_EMAIL_NOT_PROGRESSING",
        message="This action did not advance the objective.",
        severity="info",
        trigger_event_index=4,
        created_at=now,
        idempotency_key="feedback:session:4:benign",
    )

    inserted_first = repo.insert_feedback_if_absent(input=input)
    inserted_second = repo.insert_feedback_if_absent(input=input)
    db_session.flush()

    assert inserted_first is True
    assert inserted_second is False
    rows = repo.list_feedback_for_session(session_id=session.id)
    assert len(rows) == 1
    assert rows[0].idempotency_key == input.idempotency_key


def test_list_feedback_for_session_orders_by_created_at_then_event_index(
    db_session: Session,
) -> None:
    repo = SQLAlchemySessionFeedbackRepository(db=db_session)
    session = _insert_session(db_session)
    now = datetime.now(timezone.utc)

    rows = (
        SessionFeedbackCreateInput(
            session_id=session.id,
            feedback_key="f1",
            reason_code="R1",
            message="m1",
            severity="warning",
            trigger_event_index=9,
            created_at=now,
            idempotency_key="feedback:1",
        ),
        SessionFeedbackCreateInput(
            session_id=session.id,
            feedback_key="f2",
            reason_code="R2",
            message="m2",
            severity="info",
            trigger_event_index=3,
            created_at=now,
            idempotency_key="feedback:2",
        ),
        SessionFeedbackCreateInput(
            session_id=session.id,
            feedback_key="f3",
            reason_code="R3",
            message="m3",
            severity="error",
            trigger_event_index=None,
            created_at=now + timedelta(seconds=1),
            idempotency_key="feedback:3",
        ),
    )
    for row in rows:
        repo.insert_feedback_if_absent(input=row)
    db_session.flush()

    listed = repo.list_feedback_for_session(session_id=session.id)
    assert [row.feedback_key for row in listed] == ["f2", "f1", "f3"]


def test_count_unread_and_mark_read_behaviors(db_session: Session) -> None:
    repo = SQLAlchemySessionFeedbackRepository(db=db_session)
    session = _insert_session(db_session)
    now = datetime.now(timezone.utc)

    repo.insert_feedback_if_absent(
        input=SessionFeedbackCreateInput(
            session_id=session.id,
            feedback_key="u1",
            reason_code="RU1",
            message="u1",
            severity="info",
            trigger_event_index=1,
            created_at=now,
            idempotency_key="feedback:u1",
        )
    )
    repo.insert_feedback_if_absent(
        input=SessionFeedbackCreateInput(
            session_id=session.id,
            feedback_key="u2",
            reason_code="RU2",
            message="u2",
            severity="warning",
            trigger_event_index=2,
            created_at=now,
            idempotency_key="feedback:u2",
        )
    )
    db_session.flush()

    all_rows = repo.list_feedback_for_session(session_id=session.id)
    unread_before = repo.count_unread_feedback(session_id=session.id)
    marked_one = repo.mark_feedback_read(
        session_id=session.id,
        feedback_id=all_rows[0].id,
        seen_at=now + timedelta(seconds=2),
    )
    marked_one_again = repo.mark_feedback_read(
        session_id=session.id,
        feedback_id=all_rows[0].id,
        seen_at=now + timedelta(seconds=3),
    )
    marked_rest = repo.mark_all_feedback_read(
        session_id=session.id,
        seen_at=now + timedelta(seconds=4),
    )
    marked_rest_again = repo.mark_all_feedback_read(
        session_id=session.id,
        seen_at=now + timedelta(seconds=5),
    )
    db_session.flush()

    unread_after = repo.count_unread_feedback(session_id=session.id)
    assert unread_before == 2
    assert marked_one is True
    assert marked_one_again is False
    assert marked_rest == 1
    assert marked_rest_again == 0
    assert unread_after == 0
