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
    SQLAlchemySessionHintSeenRepository,
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


def test_get_session_owner_user_id_returns_owner_or_none(db_session: Session) -> None:
    repo = SQLAlchemySessionHintSeenRepository(db=db_session)
    session = _insert_session(db_session)

    owner = repo.get_session_owner_user_id(session_id=session.id)
    missing = repo.get_session_owner_user_id(session_id=uuid4())

    assert owner == session.owner_user_id
    assert missing is None


def test_mark_all_unlocked_seen_updates_only_unlocked_unseen(
    db_session: Session,
) -> None:
    repo = SQLAlchemySessionHintSeenRepository(db=db_session)
    session = _insert_session(db_session)
    now = datetime.now(timezone.utc)

    db_session.add_all(
        [
            SessionHintModel(
                id=uuid4(),
                session_id=session.id,
                hint_key="hint_unlocked_unseen",
                text="a",
                sort_order=0,
                unlock_at=now - timedelta(minutes=2),
                status="unlocked",
                unlocked_at=now - timedelta(minutes=1),
                seen_at=None,
            ),
            SessionHintModel(
                id=uuid4(),
                session_id=session.id,
                hint_key="hint_unlocked_seen",
                text="b",
                sort_order=1,
                unlock_at=now - timedelta(minutes=2),
                status="unlocked",
                unlocked_at=now - timedelta(minutes=1),
                seen_at=now - timedelta(seconds=30),
            ),
            SessionHintModel(
                id=uuid4(),
                session_id=session.id,
                hint_key="hint_pending",
                text="c",
                sort_order=2,
                unlock_at=now + timedelta(minutes=5),
                status="pending",
                unlocked_at=None,
                seen_at=None,
            ),
        ]
    )
    db_session.flush()

    seen_at = datetime.now(timezone.utc)
    updated_count = repo.mark_all_unlocked_seen(session_id=session.id, seen_at=seen_at)
    updated_count_again = repo.mark_all_unlocked_seen(
        session_id=session.id,
        seen_at=seen_at,
    )
    db_session.flush()

    rows = (
        db_session.execute(
            select(SessionHintModel)
            .where(SessionHintModel.session_id == session.id)
            .order_by(SessionHintModel.sort_order.asc())
        )
        .scalars()
        .all()
    )

    assert updated_count == 1
    assert updated_count_again == 0
    assert rows[0].hint_key == "hint_unlocked_unseen"
    assert rows[0].seen_at == seen_at
    assert rows[1].hint_key == "hint_unlocked_seen"
    assert rows[1].seen_at is not None
    assert rows[2].hint_key == "hint_pending"
    assert rows[2].seen_at is None
