from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.application.session_query.errors import (
    ForbiddenErrorSessionQuery,
)
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.session_query.types import (
    SessionHintRow,
    SessionMetadataBundleRow,
    SessionMetadataRow,
)
from apps.control_plane.src.application.session_query.service import (
    get_session_metadata,
)


class FakeSessionMetadataRepository:
    def __init__(self, row: SessionMetadataBundleRow | None) -> None:
        self._row = row

    def get_session_metadata(self, session_id: UUID) -> SessionMetadataBundleRow | None:
        return self._row


def _sample_row(state: str = "ACTIVE") -> SessionMetadataBundleRow:
    metadata = SessionMetadataRow(
        id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        owner_user_id=uuid4(),
        state=state,
        runtime_substate="WAITING_FOR_INPUT",
        resume_mode="hot_resume",
        last_transition_reason=None,
        created_at=datetime.now(timezone.utc),
        started_at=None,
        ended_at=None,
    )
    return SessionMetadataBundleRow(metadata=metadata, objectives=[], hints=[])


def test_get_session_metadata_owner_is_allowed() -> None:
    row = _sample_row()
    repo = FakeSessionMetadataRepository(row=row)

    result = get_session_metadata(
        session_id=row.metadata.id,
        principal=PrincipalContext(
            user_id=row.metadata.owner_user_id,
            role="learner",
        ),
        repo=repo,
    )

    assert result is not None
    assert result.id == row.metadata.id


def test_get_session_metadata_admin_non_owner_is_allowed() -> None:
    row = _sample_row()
    repo = FakeSessionMetadataRepository(row=row)

    result = get_session_metadata(
        session_id=row.metadata.id,
        principal=PrincipalContext(user_id=uuid4(), role="admin"),
        repo=repo,
    )

    assert result is not None
    assert result.id == row.metadata.id


def test_get_session_metadata_non_owner_non_admin_is_forbidden() -> None:
    row = _sample_row()
    repo = FakeSessionMetadataRepository(row=row)
    requester_user_id = uuid4()
    assert requester_user_id != row.metadata.owner_user_id

    with pytest.raises(ForbiddenErrorSessionQuery):
        get_session_metadata(
            session_id=row.metadata.id,
            principal=PrincipalContext(user_id=requester_user_id, role="learner"),
            repo=repo,
        )


def test_get_session_metadata_derives_interactive_true_for_active() -> None:
    row = _sample_row(state=SessionState.ACTIVE.value)
    repo = FakeSessionMetadataRepository(row=row)

    result = get_session_metadata(
        session_id=row.metadata.id,
        principal=PrincipalContext(user_id=row.metadata.owner_user_id, role="learner"),
        repo=repo,
    )

    assert result is not None
    assert result.interactive is True


def test_get_session_metadata_derives_interactive_false_for_terminal() -> None:
    row = _sample_row(state=SessionState.COMPLETED.value)
    repo = FakeSessionMetadataRepository(row=row)

    result = get_session_metadata(
        session_id=row.metadata.id,
        principal=PrincipalContext(user_id=row.metadata.owner_user_id, role="learner"),
        repo=repo,
    )

    assert result is not None
    assert result.interactive is False


def test_get_session_metadata_maps_hints_and_derives_unread_count() -> None:
    row = _sample_row(state=SessionState.ACTIVE.value)
    now = datetime.now(timezone.utc)
    row = SessionMetadataBundleRow(
        metadata=row.metadata,
        objectives=[],
        hints=[
            SessionHintRow(
                hint_key="hint_1",
                text="h1",
                sort_order=0,
                status="unlocked",
                unlock_at=now,
                unlocked_at=now,
                seen_at=None,
            ),
            SessionHintRow(
                hint_key="hint_2",
                text="h2",
                sort_order=1,
                status="unlocked",
                unlock_at=now,
                unlocked_at=now,
                seen_at=now,
            ),
            SessionHintRow(
                hint_key="hint_3",
                text="h3",
                sort_order=2,
                status="pending",
                unlock_at=now,
                unlocked_at=None,
                seen_at=None,
            ),
        ],
    )
    repo = FakeSessionMetadataRepository(row=row)

    result = get_session_metadata(
        session_id=row.metadata.id,
        principal=PrincipalContext(
            user_id=row.metadata.owner_user_id,
            role="learner",
        ),
        repo=repo,
    )

    assert result is not None
    assert [hint.hint_key for hint in result.hints] == ["hint_1", "hint_2", "hint_3"]
    assert result.unread_hint_count == 1
