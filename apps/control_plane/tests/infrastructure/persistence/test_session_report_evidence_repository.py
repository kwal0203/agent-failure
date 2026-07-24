from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from apps.control_plane.src.application.session_report_evidence.types import (
    SessionReportEvidenceItemInput,
)
from apps.control_plane.src.infrastructure.persistence.models import SessionModel
from apps.control_plane.src.infrastructure.persistence.session_report_evidence_repository import (
    SQLAlchemySessionReportEvidenceRepository,
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
    )
    db_session.add(session)
    db_session.flush()
    return session


def _item(*, position: int) -> SessionReportEvidenceItemInput:
    return SessionReportEvidenceItemInput(
        event_id=uuid4(),
        position=position,
        title=f"Title {position}",
        description=f"Description {position}",
        details={"k": position},
        occurred_at=datetime(2026, 5, 17, 21, position, 0, tzinfo=timezone.utc),
        trace_version=1,
        event_index=position,
        evidence_type="exploit_step",
        objective_keys=("lab1.token_disclosed",),
        why_it_matters="Shows exploit progression.",
        default_priority="high",
        student_note=None,
        report_section="unassigned",
        section_position=None,
    )


def test_replace_and_list_report_evidence_for_session(db_session: Session) -> None:
    repo = SQLAlchemySessionReportEvidenceRepository(db=db_session)
    session = _insert_session(db_session)

    first_batch = [_item(position=0), _item(position=1)]
    repo.replace_report_evidence_for_session(
        session_id=session.id,
        items=first_batch,
    )
    db_session.flush()

    listed_first = repo.list_report_evidence_for_session(session_id=session.id)
    assert [row.position for row in listed_first] == [0, 1]
    assert [row.title for row in listed_first] == ["Title 0", "Title 1"]

    replacement_batch = [_item(position=0)]
    repo.replace_report_evidence_for_session(
        session_id=session.id,
        items=replacement_batch,
    )
    db_session.flush()

    listed_second = repo.list_report_evidence_for_session(session_id=session.id)
    assert len(listed_second) == 1
    assert listed_second[0].title == "Title 0"
    assert listed_second[0].description == "Description 0"
    assert listed_second[0].details == {"k": 0}
    assert listed_second[0].trace_version == 1
    assert listed_second[0].event_index == 0
    assert listed_second[0].objective_keys == ("lab1.token_disclosed",)


def test_get_session_owner_user_id_returns_owner_or_none(db_session: Session) -> None:
    repo = SQLAlchemySessionReportEvidenceRepository(db=db_session)
    session = _insert_session(db_session)

    owner_user_id = repo.get_session_owner_user_id(session_id=session.id)
    missing_owner_user_id = repo.get_session_owner_user_id(session_id=uuid4())

    assert owner_user_id == session.owner_user_id
    assert missing_owner_user_id is None
