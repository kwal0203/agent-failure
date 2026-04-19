from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.models import (
    SessionHintModel,
    SessionModel,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionMetadataRepository,
)


def _insert_session(db_session: Session, *, state: SessionState) -> SessionModel:
    row = SessionModel(
        id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        owner_user_id=uuid4(),
        state=state.value,
        runtime_substate="WAITING_FOR_INPUT"
        if state in {SessionState.ACTIVE, SessionState.IDLE}
        else None,
        resume_mode="hot_resume",
        started_at=datetime.now(timezone.utc),
        ended_at=None,
        last_transition_actor="seed",
        last_transition_reason=None,
    )
    db_session.add(row)
    db_session.flush()
    return row


def test_get_session_metadata_returns_row(db_session: Session) -> None:
    row = _insert_session(db_session, state=SessionState.ACTIVE)
    repo = SQLAlchemySessionMetadataRepository(db=db_session)

    result = repo.get_session_metadata(session_id=row.id)

    assert result is not None
    assert result.metadata.id == row.id
    assert result.metadata.lab_id == row.lab_id
    assert result.metadata.lab_version_id == row.lab_version_id
    assert result.metadata.state == SessionState.ACTIVE.value
    assert result.metadata.runtime_substate == "WAITING_FOR_INPUT"
    assert result.metadata.resume_mode == "hot_resume"


def test_get_session_metadata_returns_none_for_missing(db_session: Session) -> None:
    repo = SQLAlchemySessionMetadataRepository(db=db_session)

    result = repo.get_session_metadata(session_id=uuid4())

    assert result is None


def test_get_session_metadata_returns_hints_unlocked_oldest_first(
    db_session: Session,
) -> None:
    row = _insert_session(db_session, state=SessionState.ACTIVE)
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            SessionHintModel(
                id=uuid4(),
                session_id=row.id,
                hint_key="hint_1",
                text="h1",
                sort_order=0,
                status="pending",
                unlock_at=now + timedelta(minutes=2),
                unlocked_at=None,
                seen_at=None,
            ),
            SessionHintModel(
                id=uuid4(),
                session_id=row.id,
                hint_key="hint_2",
                text="h2",
                sort_order=1,
                status="unlocked",
                unlock_at=now - timedelta(minutes=3),
                unlocked_at=now - timedelta(minutes=2),
                seen_at=None,
            ),
            SessionHintModel(
                id=uuid4(),
                session_id=row.id,
                hint_key="hint_3",
                text="h3",
                sort_order=2,
                status="unlocked",
                unlock_at=now - timedelta(minutes=6),
                unlocked_at=now - timedelta(minutes=5),
                seen_at=now - timedelta(minutes=4),
            ),
        ]
    )
    db_session.flush()

    repo = SQLAlchemySessionMetadataRepository(db=db_session)
    result = repo.get_session_metadata(session_id=row.id)

    assert result is not None
    assert [hint.hint_key for hint in result.hints] == ["hint_3", "hint_2", "hint_1"]
    assert result.hints[0].status == "unlocked"
    assert result.hints[0].seen_at is not None
    assert result.hints[2].status == "pending"
