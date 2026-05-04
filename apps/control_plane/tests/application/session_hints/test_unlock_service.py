from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4, UUID

from apps.control_plane.src.application.session_hints.service import (
    process_due_session_hints_once,
)
from apps.control_plane.src.application.session_hints.types import DueSessionHint


class _FakeProjector:
    def __init__(
        self,
        due_hints: list[DueSessionHint],
        mark_results: dict[tuple[object, str], bool],
    ) -> None:
        self._due_hints = due_hints
        self._mark_results = mark_results
        self.mark_calls: list[dict[str, object]] = []

    def claim_due_pending_hints(self, *, limit: int = 20, now: datetime | None = None):
        _ = (limit, now)
        return self._due_hints

    def mark_unlocked(
        self,
        *,
        session_id: UUID,
        hint_key: str,
        unlocked_at: datetime | None = None,
    ) -> bool:
        self.mark_calls.append(
            {"session_id": session_id, "hint_key": hint_key, "unlocked_at": unlocked_at}
        )
        return self._mark_results.get((session_id, hint_key), False)


class _FakeOutbox:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def enqueue_session_hint_unlocked(
        self,
        *,
        session_id: UUID,
        hint_key: str,
        text: str,
        sort_order: int,
        unlocked_at: datetime,
        idempotency_key: str,
    ) -> None:
        self.events.append(
            {
                "session_id": session_id,
                "hint_key": hint_key,
                "text": text,
                "sort_order": sort_order,
                "unlocked_at": unlocked_at,
                "idempotency_key": idempotency_key,
            }
        )


def test_process_due_session_hints_once_unlocks_and_emits() -> None:
    session_id = uuid4()
    now = datetime(2026, 4, 19, 19, 30, 0, tzinfo=timezone.utc)
    due_hints = [
        DueSessionHint(
            session_id=session_id,
            hint_key="hint_1",
            text="Ask what tools are available.",
            sort_order=0,
            unlock_at=now,
        )
    ]
    projector = _FakeProjector(
        due_hints=due_hints,
        mark_results={(session_id, "hint_1"): True},
    )
    outbox = _FakeOutbox()

    result = process_due_session_hints_once(projector=projector, outbox=outbox, now=now)

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.skipped_count == 0
    assert len(outbox.events) == 1
    event = outbox.events[0]
    assert event["hint_key"] == "hint_1"
    assert event["unlocked_at"] == now
    assert event["idempotency_key"] == f"hint_unlock:{session_id}:hint_1"


def test_process_due_session_hints_once_skips_when_already_unlocked() -> None:
    session_id = uuid4()
    now = datetime(2026, 4, 19, 19, 30, 0, tzinfo=timezone.utc)
    due_hints = [
        DueSessionHint(
            session_id=session_id,
            hint_key="hint_1",
            text="Ask what tools are available.",
            sort_order=0,
            unlock_at=now,
        )
    ]
    projector = _FakeProjector(
        due_hints=due_hints,
        mark_results={(session_id, "hint_1"): False},
    )
    outbox = _FakeOutbox()

    result = process_due_session_hints_once(projector=projector, outbox=outbox, now=now)

    assert result.claimed_count == 1
    assert result.succeeded_count == 0
    assert result.skipped_count == 1
    assert outbox.events == []
