from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from apps.control_plane.src.application.session_feedback.service import (
    process_pending_session_feedback_created_once,
)
from apps.control_plane.src.application.session_feedback.types import (
    PendingSessionFeedbackCreatedEvent,
    SessionFeedbackCreateInput,
    SessionFeedbackRow,
)


@dataclass(frozen=True)
class _InsertCall:
    input: SessionFeedbackCreateInput


class _FakeOutbox:
    def __init__(self, events: list[PendingSessionFeedbackCreatedEvent]) -> None:
        self._events = list(events)
        self.processed_ids: list[UUID] = []
        self.retryable_failures: list[tuple[UUID, str]] = []
        self.terminal_failures: list[tuple[UUID, str]] = []

    def claim_pending_session_feedback_created(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingSessionFeedbackCreatedEvent]:
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


class _FakeFeedbackRepo:
    def __init__(self) -> None:
        self.inserts: list[_InsertCall] = []
        self.raise_on_insert: Exception | None = None
        self._idempotency_keys: set[str] = set()

    def insert_feedback_if_absent(self, *, input: SessionFeedbackCreateInput) -> bool:
        if self.raise_on_insert is not None:
            raise self.raise_on_insert
        if input.idempotency_key in self._idempotency_keys:
            return False
        self._idempotency_keys.add(input.idempotency_key)
        self.inserts.append(_InsertCall(input=input))
        return True

    def list_feedback_for_session(
        self, *, session_id: UUID
    ) -> list[SessionFeedbackRow]:
        _ = session_id
        return []

    def count_unread_feedback(self, *, session_id: UUID) -> int:
        _ = session_id
        return 0

    def mark_feedback_read(
        self, *, session_id: UUID, feedback_id: UUID, seen_at: datetime
    ) -> bool:
        _ = (session_id, feedback_id, seen_at)
        return False

    def mark_all_feedback_read(self, *, session_id: UUID, seen_at: datetime) -> int:
        _ = (session_id, seen_at)
        return 0


def _build_event(
    *,
    outbox_event_id: UUID,
    session_id: UUID,
    created_at: datetime,
) -> PendingSessionFeedbackCreatedEvent:
    return PendingSessionFeedbackCreatedEvent(
        outbox_event_id=outbox_event_id,
        session_id=session_id,
        payload={
            "session_id": str(session_id),
            "lab_id": str(uuid4()),
            "lab_version_id": str(uuid4()),
            "feedback_key": "lab1_benign_email_not_progressing",
            "reason_code": "PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS",
            "message": "This action did not move the objective chain forward.",
            "severity": "info",
            "trigger_event_index": 12,
            "created_at": created_at.isoformat(),
            "idempotency_key": f"feedback:v1:{session_id}:12",
        },
        attempt_count=0,
        requested_at=created_at,
    )


def test_feedback_projector_valid_payload_inserts_and_marks_processed() -> None:
    session_id = uuid4()
    created_at = datetime(2026, 4, 23, 21, 0, 0, tzinfo=timezone.utc)
    outbox_event_id = uuid4()
    outbox = _FakeOutbox(
        events=[
            _build_event(
                outbox_event_id=outbox_event_id,
                session_id=session_id,
                created_at=created_at,
            )
        ]
    )
    feedback_repo = _FakeFeedbackRepo()

    result = process_pending_session_feedback_created_once(
        outbox_repo=outbox,
        feedback_repo=feedback_repo,
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert result.retried_count == 0
    assert outbox.processed_ids == [outbox_event_id]
    assert len(feedback_repo.inserts) == 1
    assert feedback_repo.inserts[0].input.session_id == session_id


def test_feedback_projector_invalid_payload_is_terminal_failure_no_write() -> None:
    session_id = uuid4()
    created_at = datetime(2026, 4, 23, 21, 5, 0, tzinfo=timezone.utc)
    outbox_event_id = uuid4()
    outbox = _FakeOutbox(
        events=[
            PendingSessionFeedbackCreatedEvent(
                outbox_event_id=outbox_event_id,
                session_id=session_id,
                payload={
                    "session_id": str(session_id),
                    # missing required contract fields intentionally
                    "idempotency_key": "invalid",
                },
                attempt_count=0,
                requested_at=created_at,
            )
        ]
    )
    feedback_repo = _FakeFeedbackRepo()

    result = process_pending_session_feedback_created_once(
        outbox_repo=outbox,
        feedback_repo=feedback_repo,
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 0
    assert result.failed_count == 1
    assert result.retried_count == 0
    assert outbox.processed_ids == []
    assert len(outbox.terminal_failures) == 1
    assert feedback_repo.inserts == []


def test_feedback_projector_duplicate_replay_is_noop_and_processed() -> None:
    session_id = uuid4()
    created_at = datetime(2026, 4, 23, 21, 10, 0, tzinfo=timezone.utc)
    outbox = _FakeOutbox(
        events=[
            _build_event(
                outbox_event_id=uuid4(),
                session_id=session_id,
                created_at=created_at,
            ),
            _build_event(
                outbox_event_id=uuid4(),
                session_id=session_id,
                created_at=created_at,
            ),
        ]
    )
    feedback_repo = _FakeFeedbackRepo()

    result = process_pending_session_feedback_created_once(
        outbox_repo=outbox,
        feedback_repo=feedback_repo,
    )

    assert result.claimed_count == 2
    assert result.succeeded_count == 2
    assert result.failed_count == 0
    assert result.retried_count == 0
    assert len(outbox.processed_ids) == 2
    assert len(feedback_repo.inserts) == 1
