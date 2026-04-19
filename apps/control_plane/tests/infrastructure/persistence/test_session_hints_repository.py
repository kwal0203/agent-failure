from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.control_plane.src.infrastructure.persistence.models import (
    SessionHintModel,
    SessionModel,
)
from apps.control_plane.src.infrastructure.persistence.session_hints_repository import (
    SQLAlchemySessionHintProjectorRepository,
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


def test_claim_due_pending_hints_returns_only_due_pending(db_session: Session) -> None:
    repo = SQLAlchemySessionHintProjectorRepository(db=db_session)
    session = _insert_session(db_session)
    now = datetime.now(timezone.utc)

    db_session.add_all(
        [
            SessionHintModel(
                id=uuid4(),
                session_id=session.id,
                hint_key="hint_due",
                text="due",
                sort_order=0,
                unlock_at=now - timedelta(seconds=5),
                status="pending",
            ),
            SessionHintModel(
                id=uuid4(),
                session_id=session.id,
                hint_key="hint_future",
                text="future",
                sort_order=1,
                unlock_at=now + timedelta(minutes=2),
                status="pending",
            ),
            SessionHintModel(
                id=uuid4(),
                session_id=session.id,
                hint_key="hint_unlocked",
                text="already unlocked",
                sort_order=2,
                unlock_at=now - timedelta(minutes=5),
                unlocked_at=now - timedelta(minutes=4),
                status="unlocked",
            ),
        ]
    )
    db_session.flush()

    claimed = repo.claim_due_pending_hints(now=now)

    assert len(claimed) == 1
    assert claimed[0].hint_key == "hint_due"
    assert claimed[0].session_id == session.id


def test_mark_unlocked_transitions_pending_once(db_session: Session) -> None:
    repo = SQLAlchemySessionHintProjectorRepository(db=db_session)
    session = _insert_session(db_session)
    now = datetime.now(timezone.utc)
    hint = SessionHintModel(
        id=uuid4(),
        session_id=session.id,
        hint_key="hint_1",
        text="h1",
        sort_order=0,
        unlock_at=now - timedelta(seconds=5),
        status="pending",
    )
    db_session.add(hint)
    db_session.flush()

    unlocked_at = datetime.now(timezone.utc)
    changed = repo.mark_unlocked(
        session_id=session.id, hint_key="hint_1", unlocked_at=unlocked_at
    )
    changed_again = repo.mark_unlocked(
        session_id=session.id, hint_key="hint_1", unlocked_at=unlocked_at
    )
    db_session.flush()

    row = db_session.execute(
        select(SessionHintModel).where(
            SessionHintModel.session_id == session.id,
            SessionHintModel.hint_key == "hint_1",
        )
    ).scalar_one()

    assert changed is True
    assert changed_again is False
    assert row.status == "unlocked"
    assert row.unlocked_at == unlocked_at
