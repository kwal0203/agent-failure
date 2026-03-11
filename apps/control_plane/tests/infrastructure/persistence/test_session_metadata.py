from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.models import SessionModel
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionMetadataRepository,
)


def _insert_session(db_session: Session, *, state: SessionState) -> SessionModel:
    row = SessionModel(
        id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
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
    assert result.id == row.id
    assert result.lab_id == row.lab_id
    assert result.lab_version_id == row.lab_version_id
    assert result.state == SessionState.ACTIVE.value
    assert result.runtime_substate == "WAITING_FOR_INPUT"
    assert result.resume_mode == "hot_resume"
    assert result.interactive is True


def test_get_session_metadata_returns_none_for_missing(db_session: Session) -> None:
    repo = SQLAlchemySessionMetadataRepository(db=db_session)

    result = repo.get_session_metadata(session_id=uuid4())

    assert result is None


def test_get_session_metadata_derives_interactive_from_state(
    db_session: Session,
) -> None:
    active_row = _insert_session(db_session, state=SessionState.ACTIVE)
    completed_row = _insert_session(db_session, state=SessionState.COMPLETED)
    repo = SQLAlchemySessionMetadataRepository(db=db_session)

    active = repo.get_session_metadata(session_id=active_row.id)
    completed = repo.get_session_metadata(session_id=completed_row.id)

    assert active is not None
    assert active.interactive is True

    assert completed is not None
    assert completed.interactive is False
