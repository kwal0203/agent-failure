from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.application.session_query.errors import (
    ForbiddenErrorSessionQuery,
)
from apps.control_plane.src.application.session_query.types import (
    SessionMetadataRow,
)
from apps.control_plane.src.application.session_query.service import (
    get_session_metadata,
)


class FakeSessionMetadataRepository:
    def __init__(self, row: SessionMetadataRow | None) -> None:
        self._row = row

    def get_session_metadata(self, session_id: UUID) -> SessionMetadataRow | None:
        return self._row


def _sample_row() -> SessionMetadataRow:
    return SessionMetadataRow(
        id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        owner_user_id=uuid4(),
        state="ACTIVE",
        runtime_substate="WAITING_FOR_INPUT",
        resume_mode="hot_resume",
        created_at=datetime.now(timezone.utc),
        started_at=None,
        ended_at=None,
    )


def test_get_session_metadata_owner_is_allowed() -> None:
    row = _sample_row()
    repo = FakeSessionMetadataRepository(row=row)

    result = get_session_metadata(
        session_id=row.id,
        principal_user_id=row.owner_user_id,
        principal_user_role="learner",
        repo=repo,
    )

    assert result is not None
    assert result.id == row.id


def test_get_session_metadata_admin_non_owner_is_allowed() -> None:
    row = _sample_row()
    repo = FakeSessionMetadataRepository(row=row)

    result = get_session_metadata(
        session_id=row.id,
        principal_user_id=uuid4(),
        principal_user_role="admin",
        repo=repo,
    )

    assert result is not None
    assert result.id == row.id


def test_get_session_metadata_non_owner_non_admin_is_forbidden() -> None:
    row = _sample_row()
    repo = FakeSessionMetadataRepository(row=row)
    requester_user_id = uuid4()
    assert requester_user_id != row.owner_user_id

    with pytest.raises(ForbiddenErrorSessionQuery):
        get_session_metadata(
            session_id=row.id,
            principal_user_id=requester_user_id,
            principal_user_role="learner",
            repo=repo,
        )


def test_get_session_metadata_derives_interactive_true_for_active() -> None:
    row = _sample_row()
    row.state = SessionState.ACTIVE.value
    repo = FakeSessionMetadataRepository(row=row)

    result = get_session_metadata(
        session_id=row.id,
        principal_user_id=row.owner_user_id,
        principal_user_role="learner",
        repo=repo,
    )

    assert result is not None
    assert result.interactive is True


def test_get_session_metadata_derives_interactive_false_for_terminal() -> None:
    row = _sample_row()
    row.state = SessionState.COMPLETED.value
    repo = FakeSessionMetadataRepository(row=row)

    result = get_session_metadata(
        session_id=row.id,
        principal_user_id=row.owner_user_id,
        principal_user_role="learner",
        repo=repo,
    )

    assert result is not None
    assert result.interactive is False
