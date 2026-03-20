from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from apps.control_plane.src.application.orchestrator.service import (
    process_cleanup_pending_once,
    process_pending_once,
)
from apps.control_plane.src.application.orchestrator.types import (
    PendingCleanupEvent,
    PendingProvisioningEvent,
    ProvisionResult,
    RuntimeProvisionRequest,
    RuntimeTeardownRequest,
    RuntimeTeardownResult,
)
from apps.control_plane.src.application.session_create.types import LabRuntimeBinding
from apps.control_plane.src.application.session_lifecycle.ports import (
    UnitOfWork as SessionLifecycleUnitOfWork,
)
from apps.control_plane.src.domain.session_lifecycle.state_machine import Trigger


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


class _FakeOutbox:
    def __init__(self, events: list[PendingProvisioningEvent]) -> None:
        self._events = events
        self.processed_calls: list[_OutboxProcessedCall] = []
        self.terminal_calls: list[_OutboxTerminalCall] = []

    def claim_pending_provisioning(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingProvisioningEvent]:
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
        _ = (outbox_event_id, error_message, backoff_seconds, failed_at)

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


class _FakeLabRepository:
    def validate_lab(self, lab_id: UUID) -> bool:
        _ = lab_id
        return True

    def get_runtime_binding(
        self, lab_id: UUID, lab_version_id: UUID
    ) -> LabRuntimeBinding:
        _ = (lab_id, lab_version_id)
        return LabRuntimeBinding(lab_slug="baseline", lab_version="0.1.0")


class _FakeResolver:
    def resolve(self, lab_slug: str, lab_version: str) -> str:
        _ = (lab_slug, lab_version)
        return "ghcr.io/test/runtime@sha256:abc123"


class _FakeProvisioner:
    def __init__(self, result: ProvisionResult) -> None:
        self._result = result
        self.requests: list[RuntimeProvisionRequest] = []

    def provision(self, request: RuntimeProvisionRequest) -> ProvisionResult:
        self.requests.append(request)
        return self._result


class _FakeProcessPendingOnceUoW:
    def __init__(self, outbox: _FakeOutbox) -> None:
        self._outbox = outbox
        self._lab = _FakeLabRepository()
        self._lifecycle_uow: SessionLifecycleUnitOfWork = object()  # type: ignore[assignment]

    @property
    def outbox(self) -> _FakeOutbox:
        return self._outbox

    @property
    def lifecycle_uow(self) -> SessionLifecycleUnitOfWork:
        return self._lifecycle_uow

    @property
    def lab(self) -> _FakeLabRepository:
        return self._lab

    @contextmanager
    def transaction(self):
        yield


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
    ) -> None:
        self._result = result
        self._raises = raises
        self.requests: list[RuntimeTeardownRequest] = []

    def teardown(self, request: RuntimeTeardownRequest) -> RuntimeTeardownResult:
        self.requests.append(request)
        if self._raises is not None:
            raise self._raises
        if self._result is None:
            raise RuntimeError("fake teardown missing result")
        return self._result


def _event(*, payload: dict[str, Any]) -> PendingProvisioningEvent:
    return PendingProvisioningEvent(
        outbox_event_id=uuid4(),
        session_id=uuid4(),
        payload=payload,
        attempt_count=0,
    )


def _cleanup_event(
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


def test_process_pending_once_success_marks_processed_and_transitions(
    monkeypatch,
) -> None:
    ev = _event(
        payload={
            "lab_id": str(uuid4()),
            "lab_version_id": str(uuid4()),
        }
    )
    outbox = _FakeOutbox(events=[ev])
    uow = _FakeProcessPendingOnceUoW(outbox=outbox)
    provisioner = _FakeProvisioner(
        result=ProvisionResult(status="accepted", runtime_id="r-1")
    )
    resolver = _FakeResolver()

    transition_calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        transition_calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        "apps.control_plane.src.application.orchestrator.service.transition_session",
        _fake_transition_session,
    )

    result = process_pending_once(
        uow=uow,
        image_resolver=resolver,
        provisioner=provisioner,
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert len(outbox.processed_calls) == 1
    assert len(outbox.terminal_calls) == 0
    assert len(transition_calls) == 1
    assert transition_calls[0]["trigger"] == Trigger.PROVISIONING_SUCCEEDED
    assert transition_calls[0]["session_id"] == ev.session_id


def test_process_pending_once_failed_provision_marks_terminal_and_transitions_failed(
    monkeypatch,
) -> None:
    ev = _event(
        payload={
            "lab_id": str(uuid4()),
            "lab_version_id": str(uuid4()),
        }
    )
    outbox = _FakeOutbox(events=[ev])
    uow = _FakeProcessPendingOnceUoW(outbox=outbox)
    provisioner = _FakeProvisioner(
        result=ProvisionResult(status="failed", reason_code="K8S_APPLY_FAILED")
    )
    resolver = _FakeResolver()

    transition_calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        transition_calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        "apps.control_plane.src.application.orchestrator.service.transition_session",
        _fake_transition_session,
    )

    result = process_pending_once(
        uow=uow,
        image_resolver=resolver,
        provisioner=provisioner,
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 0
    assert result.failed_count == 1
    assert len(outbox.processed_calls) == 0
    assert len(outbox.terminal_calls) == 1
    assert len(transition_calls) == 1
    assert transition_calls[0]["trigger"] == Trigger.PROVISIONING_FAILED
    assert transition_calls[0]["session_id"] == ev.session_id


def test_process_pending_once_malformed_payload_marks_terminal_and_skips_transition(
    monkeypatch,
) -> None:
    ev = _event(
        payload={
            "lab_id": str(uuid4()),
            "lab_version_id": 123,  # invalid shape
        }
    )
    outbox = _FakeOutbox(events=[ev])
    uow = _FakeProcessPendingOnceUoW(outbox=outbox)
    provisioner = _FakeProvisioner(
        result=ProvisionResult(status="accepted", runtime_id="r-1")
    )
    resolver = _FakeResolver()

    transition_calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        transition_calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        "apps.control_plane.src.application.orchestrator.service.transition_session",
        _fake_transition_session,
    )

    result = process_pending_once(
        uow=uow,
        image_resolver=resolver,
        provisioner=provisioner,
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 0
    assert result.failed_count == 1
    assert len(outbox.processed_calls) == 0
    assert len(outbox.terminal_calls) == 1
    assert len(provisioner.requests) == 0
    assert len(transition_calls) == 0


def test_process_cleanup_pending_once_deleted_marks_processed() -> None:
    ev = _cleanup_event(payload={"runtime_id": "pod-1"})
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
    ev = _cleanup_event(payload={"runtime_id": "pod-1"})
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


def test_process_cleanup_pending_once_retryable_failure_marks_retryable() -> None:
    ev = _cleanup_event(payload={"runtime_id": "pod-1"}, attempt_count=0)
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
    ev = _cleanup_event(payload={"runtime_id": "pod-1"}, attempt_count=3)
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
    ev = _cleanup_event(payload={"runtime_id": 123})  # invalid
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
