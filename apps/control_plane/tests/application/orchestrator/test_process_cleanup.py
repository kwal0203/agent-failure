from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from apps.control_plane.src.application.orchestrator.service import (
    process_cleanup_pending_once,
)
from apps.control_plane.src.application.orchestrator.types import (
    PendingCleanupEvent,
    RuntimeTeardownRequest,
    RuntimeTeardownResult,
)
from apps.control_plane.src.application.session_lifecycle.ports import (
    UnitOfWork as SessionLifecycleUnitOfWork,
)


@dataclass
class _OutboxProcessedCall:
    outbox_event_id: UUID
    processed_at: datetime | None


@dataclass
class _OutboxTerminalCall:
    outbox_event_id: UUID
    error_message: str
    failed_at: datetime | None


@dataclass
class _OutboxRetryableCall:
    outbox_event_id: UUID
    error_message: str
    backoff_seconds: int
    failed_at: datetime | None


class _FakeCleanupOutbox:
    def __init__(self, events: list[PendingCleanupEvent]) -> None:
        self._events = events
        self.processed_calls: list[_OutboxProcessedCall] = []
        self.retryable_calls: list[_OutboxRetryableCall] = []
        self.terminal_calls: list[_OutboxTerminalCall] = []

    def claim_pending_cleanup(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingCleanupEvent]:
        _ = (limit, now)
        return self._events

    def mark_processed(
        self, *, outbox_event_id: UUID, processed_at: datetime | None = None
    ) -> None:
        self.processed_calls.append(
            _OutboxProcessedCall(
                outbox_event_id=outbox_event_id, processed_at=processed_at
            )
        )

    def mark_retryable_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        backoff_seconds: int = 15,
        failed_at: datetime | None = None,
    ) -> None:
        self.retryable_calls.append(
            _OutboxRetryableCall(
                outbox_event_id=outbox_event_id,
                error_message=error_message,
                backoff_seconds=backoff_seconds,
                failed_at=failed_at,
            )
        )

    def mark_terminal_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        failed_at: datetime | None = None,
    ) -> None:
        self.terminal_calls.append(
            _OutboxTerminalCall(
                outbox_event_id=outbox_event_id,
                error_message=error_message,
                failed_at=failed_at,
            )
        )


class _FakeCleanupUoW:
    def __init__(self, outbox: _FakeCleanupOutbox) -> None:
        self._outbox = outbox
        self._lifecycle_uow: SessionLifecycleUnitOfWork = object()  # type: ignore[assignment]

    @property
    def outbox(self) -> _FakeCleanupOutbox:
        return self._outbox

    @property
    def lifecycle_uow(self) -> SessionLifecycleUnitOfWork:
        return self._lifecycle_uow

    @contextmanager
    def transaction(self):
        yield


class _FakeTeardown:
    def __init__(
        self,
        *,
        result: RuntimeTeardownResult | None = None,
        raises: Exception | None = None,
        resources_exist: bool | None = None,
    ) -> None:
        self._result = result
        self._raises = raises
        self._resources_exist = resources_exist
        self.requests: list[RuntimeTeardownRequest] = []

    def teardown(self, request: RuntimeTeardownRequest) -> RuntimeTeardownResult:
        self.requests.append(request)
        if self._raises is not None:
            raise self._raises
        if self._result is None:
            raise RuntimeError("fake teardown missing result")
        return self._result

    def resources_exist(self, session_id: str) -> bool:
        _ = session_id
        return bool(self._resources_exist)


def _make_cleanup_event(
    *,
    payload: dict[str, Any],
    attempt_count: int = 0,
) -> PendingCleanupEvent:
    return PendingCleanupEvent(
        outbox_event_id=uuid4(),
        session_id=uuid4(),
        payload=payload,
        attempt_count=attempt_count,
    )


def test_process_cleanup_pending_once_deleted_marks_processed() -> None:
    ev = _make_cleanup_event(payload={"runtime_id": "pod-1"})
    outbox = _FakeCleanupOutbox(events=[ev])
    uow = _FakeCleanupUoW(outbox=outbox)
    teardown = _FakeTeardown(result=RuntimeTeardownResult(status="deleted"))

    result = process_cleanup_pending_once(uow=uow, teardown=teardown)

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert result.retried_count == 0
    assert len(outbox.processed_calls) == 1
    assert len(outbox.retryable_calls) == 0
    assert len(outbox.terminal_calls) == 0


def test_process_cleanup_pending_once_already_gone_marks_processed() -> None:
    ev = _make_cleanup_event(payload={"runtime_id": "pod-1"})
    outbox = _FakeCleanupOutbox(events=[ev])
    uow = _FakeCleanupUoW(outbox=outbox)
    teardown = _FakeTeardown(result=RuntimeTeardownResult(status="already_gone"))

    result = process_cleanup_pending_once(uow=uow, teardown=teardown)

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert result.retried_count == 0
    assert len(outbox.processed_calls) == 1
    assert len(outbox.retryable_calls) == 0
    assert len(outbox.terminal_calls) == 0


def test_process_cleanup_pending_once_already_gone_terminal_first_attempt_retries() -> (
    None
):
    ev = _make_cleanup_event(
        payload={"runtime_id": "pod-1", "terminal_state": "CANCELLED"},
        attempt_count=0,
    )
    outbox = _FakeCleanupOutbox(events=[ev])
    uow = _FakeCleanupUoW(outbox=outbox)
    teardown = _FakeTeardown(result=RuntimeTeardownResult(status="already_gone"))

    result = process_cleanup_pending_once(uow=uow, teardown=teardown)

    assert result.claimed_count == 1
    assert result.succeeded_count == 0
    assert result.failed_count == 0
    assert result.retried_count == 1
    assert len(outbox.processed_calls) == 0
    assert len(outbox.retryable_calls) == 1
    assert outbox.retryable_calls[0].error_message == "CLEANUP_ALREADY_GONE_REVERIFY"
    assert len(outbox.terminal_calls) == 0


def test_process_cleanup_pending_once_retryable_failure_marks_retryable() -> None:
    ev = _make_cleanup_event(payload={"runtime_id": "pod-1"}, attempt_count=0)
    outbox = _FakeCleanupOutbox(events=[ev])
    uow = _FakeCleanupUoW(outbox=outbox)
    teardown = _FakeTeardown(
        result=RuntimeTeardownResult(
            status="failed",
            reason_code="K8S_TIMEOUT",
        )
    )

    result = process_cleanup_pending_once(uow=uow, teardown=teardown)

    assert result.claimed_count == 1
    assert result.succeeded_count == 0
    assert result.failed_count == 0
    assert result.retried_count == 1
    assert len(outbox.processed_calls) == 0
    assert len(outbox.retryable_calls) == 1
    assert len(outbox.terminal_calls) == 0


def test_process_cleanup_pending_once_failed_max_attempts_marks_terminal() -> None:
    ev = _make_cleanup_event(payload={"runtime_id": "pod-1"}, attempt_count=3)
    outbox = _FakeCleanupOutbox(events=[ev])
    uow = _FakeCleanupUoW(outbox=outbox)
    teardown = _FakeTeardown(
        result=RuntimeTeardownResult(
            status="failed",
            reason_code="K8S_TIMEOUT",
        )
    )

    result = process_cleanup_pending_once(uow=uow, teardown=teardown)

    assert result.claimed_count == 1
    assert result.succeeded_count == 0
    assert result.failed_count == 1
    assert result.retried_count == 0
    assert len(outbox.processed_calls) == 0
    assert len(outbox.retryable_calls) == 0
    assert len(outbox.terminal_calls) == 1


def test_process_cleanup_pending_once_invalid_payload_marks_terminal() -> None:
    ev = _make_cleanup_event(payload={"runtime_id": 123})  # invalid
    outbox = _FakeCleanupOutbox(events=[ev])
    uow = _FakeCleanupUoW(outbox=outbox)
    teardown = _FakeTeardown(result=RuntimeTeardownResult(status="deleted"))

    result = process_cleanup_pending_once(uow=uow, teardown=teardown)

    assert result.claimed_count == 1
    assert result.succeeded_count == 0
    assert result.failed_count == 1
    assert result.retried_count == 0
    assert len(outbox.processed_calls) == 0
    assert len(outbox.retryable_calls) == 0
    assert len(outbox.terminal_calls) == 1
    assert len(teardown.requests) == 0


def test_process_cleanup_pending_once_deleted_but_resources_still_exist_retries() -> (
    None
):
    ev = _make_cleanup_event(payload={"runtime_id": "pod-1"}, attempt_count=0)
    outbox = _FakeCleanupOutbox(events=[ev])
    uow = _FakeCleanupUoW(outbox=outbox)
    teardown = _FakeTeardown(
        result=RuntimeTeardownResult(status="deleted"),
        resources_exist=True,
    )

    result = process_cleanup_pending_once(uow=uow, teardown=teardown)

    assert result.claimed_count == 1
    assert result.succeeded_count == 0
    assert result.failed_count == 0
    assert result.retried_count == 1
    assert len(outbox.processed_calls) == 0
    assert len(outbox.retryable_calls) == 1
    assert outbox.retryable_calls[0].error_message == "CLEANUP_RESOURCES_STILL_EXIST"


def test_process_cleanup_pending_once_teardown_resources_still_exist_retries() -> None:
    ev = _make_cleanup_event(payload={"runtime_id": "pod-1"}, attempt_count=0)
    outbox = _FakeCleanupOutbox(events=[ev])
    uow = _FakeCleanupUoW(outbox=outbox)
    teardown = _FakeTeardown(
        result=RuntimeTeardownResult(
            status="failed",
            reason_code="K8S_RESOURCES_STILL_EXIST",
        )
    )

    result = process_cleanup_pending_once(uow=uow, teardown=teardown)

    assert result.claimed_count == 1
    assert result.succeeded_count == 0
    assert result.failed_count == 0
    assert result.retried_count == 1
    assert len(outbox.processed_calls) == 0
    assert len(outbox.retryable_calls) == 1
    assert outbox.retryable_calls[0].error_message == "K8S_RESOURCES_STILL_EXIST"
    assert len(outbox.terminal_calls) == 0
