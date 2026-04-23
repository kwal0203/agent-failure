from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from apps.contracts.src.types import CompletionOutcome
from apps.control_plane.src.application.session_completion.service import (
    process_pending_session_completed_once,
)
from apps.control_plane.src.application.session_completion.types import (
    CompletionStatus,
    PendingSessionCompletedEvent,
    SessionCompletionState,
)


@dataclass(frozen=True)
class _WriteCall:
    session_id: UUID
    completion_status: CompletionStatus
    completed_at: datetime
    completion_reason_code: str | None


class _FakeOutbox:
    def __init__(self, events: list[PendingSessionCompletedEvent]) -> None:
        self._events = list(events)
        self.processed_ids: list[UUID] = []
        self.retryable_failures: list[tuple[UUID, str]] = []
        self.terminal_failures: list[tuple[UUID, str]] = []

    def claim_pending_session_completed(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingSessionCompletedEvent]:
        _ = now
        claimed = self._events[:limit]
        self._events = self._events[limit:]
        return claimed

    def mark_processed(
        self, *, outbox_event_id: UUID, processed_at: datetime | None = None
    ) -> None:
        _ = processed_at
        self.processed_ids.append(outbox_event_id)

    def mark_retryable_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        backoff_seconds: int = 15,
        failed_at: datetime | None = None,
    ) -> None:
        _ = (backoff_seconds, failed_at)
        self.retryable_failures.append((outbox_event_id, error_message))

    def mark_terminal_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        failed_at: datetime | None = None,
    ) -> None:
        _ = failed_at
        self.terminal_failures.append((outbox_event_id, error_message))


class _FakeCompletionWriter:
    def __init__(self, state: SessionCompletionState | None) -> None:
        self._state = state
        self.calls: list[_WriteCall] = []
        self.raise_on_write: Exception | None = None

    def get_completion_state(
        self, *, session_id: UUID
    ) -> SessionCompletionState | None:
        _ = session_id
        return self._state

    def mark_completion_if_in_progress(
        self,
        *,
        session_id: UUID,
        completion_status: CompletionStatus,
        completed_at: datetime,
        completion_reason_code: str | None,
    ) -> bool:
        if self.raise_on_write is not None:
            raise self.raise_on_write
        self.calls.append(
            _WriteCall(
                session_id=session_id,
                completion_status=completion_status,
                completed_at=completed_at,
                completion_reason_code=completion_reason_code,
            )
        )
        if self._state is not None and self._state.completion_status == "in_progress":
            self._state = SessionCompletionState(
                completion_status=completion_status,
                completed_at=completed_at,
                completion_reason_code=completion_reason_code,
            )
            return True
        return False


def _build_event(
    *,
    outbox_event_id: UUID,
    session_id: UUID,
    occurred_at: datetime,
    outcome: CompletionOutcome = "completed_success",
    completion_reason_code: str | None = "ALL_REQUIRED_OBJECTIVES_COMPLETED",
    trigger_event_index: int | None = 42,
) -> PendingSessionCompletedEvent:
    return PendingSessionCompletedEvent(
        outbox_event_id=outbox_event_id,
        session_id=session_id,
        payload={
            "session_id": str(session_id),
            "lab_id": str(uuid4()),
            "lab_version_id": str(uuid4()),
            "outcome": outcome,
            "completion_reason_code": completion_reason_code,
            "trigger_event_index": trigger_event_index,
            "occurred_at": occurred_at.isoformat(),
            "idempotency_key": f"session_completed:{session_id}:key",
        },
        attempt_count=0,
        requested_at=occurred_at,
    )


def test_completion_projector_applies_terminal_state_once() -> None:
    session_id = uuid4()
    occurred_at = datetime(2026, 4, 22, 21, 0, 0, tzinfo=timezone.utc)
    outbox_event_id = uuid4()
    outbox = _FakeOutbox(
        events=[
            _build_event(
                outbox_event_id=outbox_event_id,
                session_id=session_id,
                occurred_at=occurred_at,
            )
        ]
    )
    completion_writer = _FakeCompletionWriter(
        state=SessionCompletionState(
            completion_status="in_progress",
            completed_at=None,
            completion_reason_code=None,
        )
    )

    result = process_pending_session_completed_once(
        outbox_repo=outbox,
        completion_writer=completion_writer,
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert result.retried_count == 0
    assert outbox.processed_ids == [outbox_event_id]
    assert len(completion_writer.calls) == 1
    assert completion_writer.calls[0].completion_status == "completed_success"


def test_completion_projector_duplicate_replay_is_terminal_no_op() -> None:
    session_id = uuid4()
    occurred_at = datetime(2026, 4, 22, 21, 5, 0, tzinfo=timezone.utc)
    outbox_event_id = uuid4()
    outbox = _FakeOutbox(
        events=[
            _build_event(
                outbox_event_id=outbox_event_id,
                session_id=session_id,
                occurred_at=occurred_at,
            )
        ]
    )
    completion_writer = _FakeCompletionWriter(
        state=SessionCompletionState(
            completion_status="completed_success",
            completed_at=occurred_at,
            completion_reason_code="ALL_REQUIRED_OBJECTIVES_COMPLETED",
        )
    )

    result = process_pending_session_completed_once(
        outbox_repo=outbox,
        completion_writer=completion_writer,
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert result.retried_count == 0
    assert outbox.processed_ids == [outbox_event_id]
    assert completion_writer.calls == []


def test_completion_projector_invalid_payload_is_terminal_failure() -> None:
    session_id = uuid4()
    occurred_at = datetime(2026, 4, 22, 21, 10, 0, tzinfo=timezone.utc)
    outbox_event_id = uuid4()
    outbox = _FakeOutbox(
        events=[
            PendingSessionCompletedEvent(
                outbox_event_id=outbox_event_id,
                session_id=session_id,
                payload={
                    "session_id": str(session_id),
                    # missing required contract fields intentionally
                    "idempotency_key": "invalid",
                },
                attempt_count=0,
                requested_at=occurred_at,
            )
        ]
    )
    completion_writer = _FakeCompletionWriter(
        state=SessionCompletionState(
            completion_status="in_progress",
            completed_at=None,
            completion_reason_code=None,
        )
    )

    result = process_pending_session_completed_once(
        outbox_repo=outbox,
        completion_writer=completion_writer,
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 0
    assert result.failed_count == 1
    assert result.retried_count == 0
    assert outbox.processed_ids == []
    assert len(outbox.terminal_failures) == 1
    assert completion_writer.calls == []


def test_completion_projector_write_error_marks_retryable_failure() -> None:
    session_id = uuid4()
    occurred_at = datetime(2026, 4, 22, 21, 15, 0, tzinfo=timezone.utc)
    outbox_event_id = uuid4()
    outbox = _FakeOutbox(
        events=[
            _build_event(
                outbox_event_id=outbox_event_id,
                session_id=session_id,
                occurred_at=occurred_at,
            )
        ]
    )
    completion_writer = _FakeCompletionWriter(
        state=SessionCompletionState(
            completion_status="in_progress",
            completed_at=None,
            completion_reason_code=None,
        )
    )
    completion_writer.raise_on_write = RuntimeError("db unavailable")

    result = process_pending_session_completed_once(
        outbox_repo=outbox,
        completion_writer=completion_writer,
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 0
    assert result.failed_count == 0
    assert result.retried_count == 1
    assert outbox.processed_ids == []
    assert len(outbox.retryable_failures) == 1
