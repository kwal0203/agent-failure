from datetime import datetime, timedelta, timezone
from uuid import uuid4, UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from apps.control_plane.src.application.common.errors import (
    DuplicateIdempotencyKeyError,
)
from apps.control_plane.src.application.learner_explanation.types import (
    LearnerExplanationInput,
)
from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.learner_explanation_repository import (
    LearnerExplanationRepository,
)
from apps.control_plane.src.infrastructure.persistence.models import (
    LearnerExplanationModel,
    SessionModel,
)


def _seed_session(db_session: Session) -> SessionModel:
    row = SessionModel(
        id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        owner_user_id=uuid4(),
        state=SessionState.COMPLETED.value,
        runtime_substate=None,
        resume_mode="hot_resume",
        last_transition_actor="seed",
        last_transition_reason=None,
    )
    db_session.add(row)
    db_session.flush()
    return row


def _input_for(
    session: SessionModel, *, key: str, explanation: str
) -> LearnerExplanationInput:
    assert session.lab_id is not None
    assert session.lab_version_id is not None
    return LearnerExplanationInput(
        explanation=explanation,
        session_id=session.id,
        lab_id=session.lab_id,
        lab_version_id=session.lab_version_id,
        actor_user_id=session.owner_user_id,
        idempotency_key=key,
        source="learner",
    )


def test_get_by_session_and_idempotency_key_returns_existing_row(
    db_session: Session,
) -> None:
    session = _seed_session(db_session)
    repo = LearnerExplanationRepository(db=db_session)
    inserted = repo.inject_learner_explanation(
        _input_for(
            session, key="repo-idempo-1", explanation="first valid explanation text"
        )
    )

    fetched = repo.get_by_session_and_idempotency_key(
        session_id=session.id,
        idempotency_key="repo-idempo-1",
    )

    assert fetched is not None
    assert fetched.explanation_id == inserted.explanation_id
    assert fetched.session_id == session.id


def test_get_latest_for_session_returns_most_recent_attempt(
    db_session: Session,
) -> None:
    session = _seed_session(db_session)
    earlier = datetime.now(timezone.utc) - timedelta(minutes=1)
    later = datetime.now(timezone.utc)

    first = LearnerExplanationModel(
        explanation_id=uuid4(),
        explanation="first explanation",
        session_id=session.id,
        lab_id=session.lab_id,
        lab_version_id=session.lab_version_id,
        source="learner",
        actor_user_id=session.owner_user_id,
        idempotency_key="repo-latest-1",
        created_at=earlier,
    )
    second = LearnerExplanationModel(
        explanation_id=uuid4(),
        explanation="second explanation",
        session_id=session.id,
        lab_id=session.lab_id,
        lab_version_id=session.lab_version_id,
        source="learner",
        actor_user_id=session.owner_user_id,
        idempotency_key="repo-latest-2",
        created_at=later,
    )
    db_session.add(first)
    db_session.add(second)
    db_session.flush()

    repo = LearnerExplanationRepository(db=db_session)
    latest = repo.get_latest_for_session(session_id=session.id)

    assert latest is not None
    assert latest.explanation_id == second.explanation_id


def test_inject_learner_explanation_returns_existing_for_same_idempotency_key(
    db_session: Session,
) -> None:
    session = _seed_session(db_session)
    repo = LearnerExplanationRepository(db=db_session)

    first = repo.inject_learner_explanation(
        _input_for(session, key="repo-replay-1", explanation="same attempt")
    )
    second = repo.inject_learner_explanation(
        _input_for(session, key="repo-replay-1", explanation="same attempt")
    )

    assert second.explanation_id == first.explanation_id

    count = db_session.execute(
        select(func.count())
        .select_from(LearnerExplanationModel)
        .where(LearnerExplanationModel.session_id == session.id)
    ).scalar_one()
    assert count == 1


def test_inject_learner_explanation_maps_unique_constraint_to_duplicate_idempotency_error(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _seed_session(db_session)
    repo = LearnerExplanationRepository(db=db_session)

    original_get = repo.get_by_session_and_idempotency_key

    def _always_none(*, session_id: UUID, idempotency_key: str):
        _ = (session_id, idempotency_key)
        return None

    monkeypatch.setattr(repo, "get_by_session_and_idempotency_key", _always_none)

    class _Diag:
        constraint_name = "uq_learner_explanations_idempo"

    class _OrigExc(Exception):
        diag = _Diag()

    def _raise_integrity() -> None:
        raise IntegrityError("INSERT", params=None, orig=_OrigExc())

    monkeypatch.setattr(db_session, "flush", _raise_integrity)

    with pytest.raises(DuplicateIdempotencyKeyError) as exc:
        repo.inject_learner_explanation(
            _input_for(session, key="repo-race-1", explanation="race attempt")
        )

    assert exc.value.code == "DUPLICATE_IDEMPOTENCY_KEY"
    assert exc.value.details["constraint"] == "uq_learner_explanations_idempo"

    # Ensure monkeypatching doesn't leak.
    monkeypatch.setattr(repo, "get_by_session_and_idempotency_key", original_get)
