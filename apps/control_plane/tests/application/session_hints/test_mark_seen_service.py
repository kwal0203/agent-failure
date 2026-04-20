from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.session_hints.errors import (
    ForbiddenErrorSessionHints,
    SessionNotFoundErrorSessionHints,
)
from apps.control_plane.src.application.session_hints.service import (
    mark_session_hints_seen,
)


class _FakeSeenRepo:
    def __init__(self, *, owner_user_id: UUID | None, updated_count: int = 0) -> None:
        self._owner_user_id = owner_user_id
        self._updated_count = updated_count
        self.last_mark_call: dict[str, object] | None = None

    def get_session_owner_user_id(self, *, session_id: UUID) -> UUID | None:
        _ = session_id
        return self._owner_user_id

    def mark_all_unlocked_seen(self, *, session_id: UUID, seen_at: datetime) -> int:
        self.last_mark_call = {"session_id": session_id, "seen_at": seen_at}
        return self._updated_count


def test_mark_session_hints_seen_owner_marks_all_unlocked() -> None:
    user_id = uuid4()
    session_id = uuid4()
    now = datetime(2026, 4, 19, 22, 30, 0, tzinfo=timezone.utc)
    repo = _FakeSeenRepo(owner_user_id=user_id, updated_count=2)

    updated = mark_session_hints_seen(
        session_id=session_id,
        principal=PrincipalContext(user_id=user_id, role="learner"),
        seen_repo=repo,
        now=now,
    )

    assert updated == 2
    assert repo.last_mark_call == {"session_id": session_id, "seen_at": now}


def test_mark_session_hints_seen_admin_allowed_for_non_owner() -> None:
    owner_user_id = uuid4()
    session_id = uuid4()
    now = datetime(2026, 4, 19, 22, 30, 0, tzinfo=timezone.utc)
    repo = _FakeSeenRepo(owner_user_id=owner_user_id, updated_count=1)

    updated = mark_session_hints_seen(
        session_id=session_id,
        principal=PrincipalContext(user_id=uuid4(), role="admin"),
        seen_repo=repo,
        now=now,
    )

    assert updated == 1
    assert repo.last_mark_call == {"session_id": session_id, "seen_at": now}


def test_mark_session_hints_seen_forbidden_for_non_owner_non_admin() -> None:
    owner_user_id = uuid4()
    repo = _FakeSeenRepo(owner_user_id=owner_user_id, updated_count=1)

    with pytest.raises(ForbiddenErrorSessionHints):
        mark_session_hints_seen(
            session_id=uuid4(),
            principal=PrincipalContext(user_id=uuid4(), role="learner"),
            seen_repo=repo,
        )


def test_mark_session_hints_seen_raises_not_found_when_session_missing() -> None:
    repo = _FakeSeenRepo(owner_user_id=None)

    with pytest.raises(SessionNotFoundErrorSessionHints):
        mark_session_hints_seen(
            session_id=uuid4(),
            principal=PrincipalContext(user_id=uuid4(), role="admin"),
            seen_repo=repo,
        )
