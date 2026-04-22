from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
import apps.control_plane.src.application.orchestrator.service as orchestrator_service

from apps.control_plane.src.application.orchestrator.service import (
    process_cleanup_pending_once,
    process_expiry_once,
    process_pending_once,
    process_reconciliation_once,
)
from apps.control_plane.src.application.orchestrator.types import (
    ExpiryCandidate,
    PendingCleanupEvent,
    PendingProvisioningEvent,
    ProvisionResult,
    ReconciliationCandidate,
    RuntimeInspectorRequest,
    RuntimeInspectorResult,
    RuntimeProvisionRequest,
    RuntimeTeardownRequest,
    RuntimeTeardownResult,
)
from apps.control_plane.src.application.common.types import (
    GetLabCatalogRow,
    LabRuntimeBinding,
)
from apps.control_plane.src.application.session_lifecycle.ports import (
    UnitOfWork as SessionLifecycleUnitOfWork,
)
from apps.control_plane.src.application.trace.types import TraceEvent
from apps.control_plane.src.domain.session_lifecycle.state_machine import Trigger
from apps.control_plane.src.application.session_hints.types import HintTemplate


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
        self.retryable_calls: list[_OutboxRetryableCall] = []

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


class _FakeLabRepository:
    def get_lab_catalog(self) -> list[GetLabCatalogRow]:
        return []

    def validate_lab(self, lab_id: UUID) -> bool:
        _ = lab_id
        return True

    def get_runtime_binding(
        self, lab_id: UUID, lab_version_id: UUID
    ) -> LabRuntimeBinding:
        _ = (lab_id, lab_version_id)
        return LabRuntimeBinding(lab_slug="baseline", lab_version="0.1.0")

    def get_active_version_id(self, lab_id: UUID) -> UUID | None:
        _ = lab_id
        return None


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


class _FakeTraceRepo:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []
        self._next_index = 0

    def append_trace_event(self, trace: TraceEvent) -> None:
        self.events.append(trace)

    def list_trace_events_for_session(self, session_id: UUID) -> tuple[TraceEvent, ...]:
        _ = session_id
        return tuple(self.events)

    def get_next_event_index(self, session_id: UUID) -> int:
        _ = session_id
        index = self._next_index
        self._next_index += 1
        return index


class _FakeTraceOutbox:
    def enqueue_for_evaluator(
        self,
        *,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        evaluator_version: int,
        start_event_index: int,
        end_event_index: int,
        requested_at: datetime | None = None,
    ) -> None:
        _ = (
            session_id,
            lab_id,
            lab_version_id,
            evaluator_version,
            start_event_index,
            end_event_index,
            requested_at,
        )


class _FakeLifecycleUoW:
    def __init__(self) -> None:
        self._trace = _FakeTraceRepo()
        self._outbox = _FakeTraceOutbox()

    @property
    def trace(self) -> _FakeTraceRepo:
        return self._trace

    @property
    def outbox(self) -> _FakeTraceOutbox:
        return self._outbox

    @contextmanager
    def transaction(self):
        yield


class _FakeProcessPendingOnceUoW:
    def __init__(self, outbox: _FakeOutbox) -> None:
        self._outbox = outbox
        self._lab = _FakeLabRepository()
        self._lifecycle_uow: SessionLifecycleUnitOfWork = _FakeLifecycleUoW()  # type: ignore[assignment]
        self._trace = _FakeTraceRepo()
        self._runtime_binding = _FakeRuntimeBindingRepo()
        self._objective_templates = _FakeObjectiveTemplateRepo()
        self._session_objectives = _FakeSessionObjectiveWriter()
        self._hint_templates = _FakeHintTemplateRepo()
        self._session_hints = _FakeSessionHintWriter()

    @property
    def outbox(self) -> _FakeOutbox:
        return self._outbox

    @property
    def lifecycle_uow(self) -> SessionLifecycleUnitOfWork:
        return self._lifecycle_uow

    @property
    def lab(self) -> _FakeLabRepository:
        return self._lab

    @property
    def trace(self) -> _FakeTraceRepo:
        return self._trace

    @property
    def runtime_binding(self) -> "_FakeRuntimeBindingRepo":
        return self._runtime_binding

    @property
    def objective_templates(self) -> "_FakeObjectiveTemplateRepo":
        return self._objective_templates

    @property
    def session_objectives(self) -> "_FakeSessionObjectiveWriter":
        return self._session_objectives

    @property
    def hint_templates(self) -> "_FakeHintTemplateRepo":
        return self._hint_templates

    @property
    def session_hints(self) -> "_FakeSessionHintWriter":
        return self._session_hints

    @contextmanager
    def transaction(self):
        yield


class _FakeRuntimeBindingRepo:
    def __init__(self) -> None:
        self.upsert_calls: list[Any] = []

    def upsert_runtime_binding(self, *, input: Any) -> None:
        self.upsert_calls.append(input)


class _FakeObjectiveTemplateRepo:
    def list_objective_templates(
        self, lab_version_id: UUID
    ) -> list[tuple[str, str, int]]:
        _ = lab_version_id
        return []


class _FakeSessionObjectiveWriter:
    def upsert_objective(
        self,
        session_id: UUID,
        objective_key: str,
        label: str,
        sort_order: int,
    ) -> None:
        _ = (session_id, objective_key, label, sort_order)

    def mark_complete(
        self,
        *,
        session_id: UUID,
        objective_key: str,
        completed_at: datetime | None = None,
    ) -> None:
        _ = (session_id, objective_key, completed_at)

    def list_objective_states(self, *, session_id: UUID) -> list[tuple[str, str]]:
        _ = session_id
        return []


class _FakeHintTemplateRepo:
    def list_hint_templates(self, lab_version_id: UUID) -> list[HintTemplate]:
        _ = lab_version_id
        return []


class _FakeSessionHintWriter:
    def __init__(self) -> None:
        self.upsert_calls: list[dict[str, Any]] = []

    def upsert_hint(
        self,
        *,
        session_id: UUID,
        hint_key: str,
        text: str,
        sort_order: int,
        unlock_at: datetime,
    ) -> None:
        self.upsert_calls.append(
            {
                "session_id": session_id,
                "hint_key": hint_key,
                "text": text,
                "sort_order": sort_order,
                "unlock_at": unlock_at,
            }
        )


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


class _FakeReconciliationQueryRepo:
    def __init__(self, sessions: list[ReconciliationCandidate]) -> None:
        self._sessions = sessions

    def get_reconciliation_candidates(
        self, *, limit: int = 100
    ) -> list[ReconciliationCandidate]:
        _ = limit
        return self._sessions


class _FakeExpiryQueryRepo:
    def __init__(self, sessions: list[ExpiryCandidate]) -> None:
        self._sessions = sessions

    def get_expiry_candidates(self, *, limit: int = 100) -> list[ExpiryCandidate]:
        _ = limit
        return self._sessions


class _FakeReconciliationOutbox:
    def __init__(self) -> None:
        self.cleanup_enqueues: list[dict[str, Any]] = []

    def enqueue_for_cleanup(
        self,
        *,
        session_id: UUID,
        runtime_id: str | None,
        terminal_state: str | None,
        reason_code: str | None,
        requested_at: datetime | None,
    ) -> None:
        self.cleanup_enqueues.append(
            {
                "session_id": session_id,
                "runtime_id": runtime_id,
                "terminal_state": terminal_state,
                "reason_code": reason_code,
                "requested_at": requested_at,
            }
        )


class _FakeReconciliationUoW:
    def __init__(self) -> None:
        self._outbox = _FakeReconciliationOutbox()
        self._trace = _FakeTraceRepo()

    @property
    def outbox(self) -> _FakeReconciliationOutbox:
        return self._outbox

    @property
    def trace(self) -> _FakeTraceRepo:
        return self._trace

    @contextmanager
    def transaction(self):
        yield


class _FakeInspector:
    def __init__(self, responses: dict[UUID, RuntimeInspectorResult]) -> None:
        self._responses = responses

    def inspect(self, request: RuntimeInspectorRequest) -> RuntimeInspectorResult:
        result = self._responses.get(request.session_id)
        if result is None:
            return RuntimeInspectorResult(
                session_id=request.session_id,
                requested_runtime_id=request.runtime_id,
                matched_runtime_ids=tuple(),
                exists=True,
                duplicate_count=0,
                phase="Running",
                ready=True,
                reason=None,
                details=None,
            )
        return result


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
    monkeypatch: pytest.MonkeyPatch,
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
        result=ProvisionResult(
            status="accepted",
            runtime_id="r-1",
            details={"base_url": "http://runtime.test.local:8000"},
        )
    )
    inspector = _FakeInspector(responses={})
    resolver = _FakeResolver()

    transition_calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        transition_calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        orchestrator_service, "transition_session", _fake_transition_session
    )

    result = process_pending_once(
        uow=uow,
        image_resolver=resolver,
        provisioner=provisioner,
        runtime_inspector=inspector,
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert len(outbox.processed_calls) == 1
    assert len(outbox.terminal_calls) == 0
    assert len(transition_calls) == 1
    assert transition_calls[0]["trigger"] == Trigger.PROVISIONING_SUCCEEDED
    assert transition_calls[0]["session_id"] == ev.session_id
    assert len(provisioner.requests) == 1
    assert provisioner.requests[0].lab_difficulty == "medium"


def test_process_pending_once_failed_provision_marks_terminal_and_transitions_failed(
    monkeypatch: pytest.MonkeyPatch,
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
    inspector = _FakeInspector(responses={})
    resolver = _FakeResolver()

    transition_calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        transition_calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        orchestrator_service, "transition_session", _fake_transition_session
    )

    result = process_pending_once(
        uow=uow,
        image_resolver=resolver,
        provisioner=provisioner,
        runtime_inspector=inspector,
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 0
    assert result.failed_count == 1
    assert len(outbox.processed_calls) == 0
    assert len(outbox.terminal_calls) == 1
    assert len(transition_calls) == 1
    assert transition_calls[0]["trigger"] == Trigger.PROVISIONING_FAILED
    assert transition_calls[0]["session_id"] == ev.session_id


def test_process_pending_once_explicit_difficulty_propagates_to_runtime_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ev = _event(
        payload={
            "lab_id": str(uuid4()),
            "lab_version_id": str(uuid4()),
            "lab_difficulty": "easy",
        }
    )
    outbox = _FakeOutbox(events=[ev])
    uow = _FakeProcessPendingOnceUoW(outbox=outbox)
    provisioner = _FakeProvisioner(
        result=ProvisionResult(
            status="accepted",
            runtime_id="r-1",
            details={"base_url": "http://runtime.test.local:8000"},
        )
    )
    inspector = _FakeInspector(responses={})
    resolver = _FakeResolver()

    transition_calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        transition_calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        orchestrator_service, "transition_session", _fake_transition_session
    )

    result = process_pending_once(
        uow=uow,
        image_resolver=resolver,
        provisioner=provisioner,
        runtime_inspector=inspector,
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert len(outbox.processed_calls) == 1
    assert len(outbox.terminal_calls) == 0
    assert len(transition_calls) == 1
    assert transition_calls[0]["trigger"] == Trigger.PROVISIONING_SUCCEEDED
    assert transition_calls[0]["session_id"] == ev.session_id
    assert len(provisioner.requests) == 1
    assert provisioner.requests[0].lab_difficulty == "easy"


def test_process_pending_once_malformed_payload_marks_terminal_and_skips_transition(
    monkeypatch: pytest.MonkeyPatch,
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
        result=ProvisionResult(
            status="accepted",
            runtime_id="r-1",
            details={"base_url": "http://runtime.test.local:8000"},
        )
    )
    inspector = _FakeInspector(responses={})
    resolver = _FakeResolver()

    transition_calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        transition_calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        orchestrator_service, "transition_session", _fake_transition_session
    )

    result = process_pending_once(
        uow=uow,
        image_resolver=resolver,
        provisioner=provisioner,
        runtime_inspector=inspector,
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 0
    assert result.failed_count == 1
    assert len(outbox.processed_calls) == 0
    assert len(outbox.terminal_calls) == 1
    assert len(provisioner.requests) == 0
    assert len(transition_calls) == 0


def test_process_pending_once_not_ready_marks_retryable_and_emits_pending_trace(
    monkeypatch: pytest.MonkeyPatch,
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
        result=ProvisionResult(
            status="accepted",
            runtime_id="r-1",
            details={"base_url": "http://runtime.test.local:8000"},
        )
    )
    inspector = _FakeInspector(
        responses={
            ev.session_id: RuntimeInspectorResult(
                session_id=ev.session_id,
                requested_runtime_id="r-1",
                matched_runtime_ids=tuple(),
                exists=True,
                duplicate_count=0,
                phase="Pending",
                ready=False,
                reason=None,
                details=None,
            )
        }
    )
    resolver = _FakeResolver()

    transition_calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        transition_calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        orchestrator_service, "transition_session", _fake_transition_session
    )
    # Keep readiness loop deterministic and fast in test.
    ticks = iter([0.0, 0.0, 31.0])
    monkeypatch.setattr(orchestrator_service.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(orchestrator_service.time, "sleep", lambda _seconds: None)

    result = process_pending_once(
        uow=uow,
        image_resolver=resolver,
        provisioner=provisioner,
        runtime_inspector=inspector,
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 0
    assert result.failed_count == 0
    assert result.retried_count == 1
    assert len(outbox.processed_calls) == 0
    assert len(outbox.terminal_calls) == 0
    assert len(outbox.retryable_calls) == 1
    assert len(transition_calls) == 0
    lifecycle_trace = cast(_FakeTraceRepo, uow.lifecycle_uow.trace)
    assert len(lifecycle_trace.events) == 2
    assert [event.event_type for event in lifecycle_trace.events] == [
        "RUNTIME_PROVISION_REQUESTED",
        "RUNTIME_PROVISION_PENDING",
    ]


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


def test_process_reconciliation_once_missing_runtime_transitions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = uuid4()
    candidate = ReconciliationCandidate(
        state="ACTIVE",
        session_id=session_id,
        runtime_id="runtime-1",
        runtime_substate=None,
    )
    repo = _FakeReconciliationQueryRepo([candidate])
    uow = _FakeReconciliationUoW()
    inspector = _FakeInspector(
        {
            session_id: RuntimeInspectorResult(
                session_id=session_id,
                requested_runtime_id="runtime-1",
                matched_runtime_ids=tuple(),
                exists=False,
                duplicate_count=0,
                phase=None,
                ready=None,
                reason="NotFound",
            )
        }
    )

    calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        orchestrator_service, "transition_session", _fake_transition_session
    )

    result = process_reconciliation_once(
        session_query_repo=repo,
        uow=uow,  # type: ignore[arg-type]
        inspector=inspector,  # type: ignore[arg-type]
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert len(calls) == 1
    assert calls[0]["trigger"] == Trigger.RUNTIME_FAILED


def test_process_reconciliation_once_terminal_with_runtime_enqueues_cleanup() -> None:
    session_id = uuid4()
    candidate = ReconciliationCandidate(
        state="FAILED",
        session_id=session_id,
        runtime_id="runtime-1",
        runtime_substate=None,
    )
    repo = _FakeReconciliationQueryRepo([candidate])
    uow = _FakeReconciliationUoW()
    inspector = _FakeInspector(
        {
            session_id: RuntimeInspectorResult(
                session_id=session_id,
                requested_runtime_id="runtime-1",
                matched_runtime_ids=("runtime-1",),
                exists=True,
                duplicate_count=0,
                phase="Failed",
                ready=False,
                reason="CrashLoopBackOff",
            )
        }
    )

    result = process_reconciliation_once(
        session_query_repo=repo,
        uow=uow,  # type: ignore[arg-type]
        inspector=inspector,  # type: ignore[arg-type]
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert len(uow.outbox.cleanup_enqueues) == 1
    assert uow.outbox.cleanup_enqueues[0]["reason_code"] == "ORPHAN_RUNTIME_DETECTED"


def test_process_reconciliation_once_duplicate_runtimes_enqueues_extras_only() -> None:
    session_id = uuid4()
    candidate = ReconciliationCandidate(
        state="ACTIVE",
        session_id=session_id,
        runtime_id="runtime-1",
        runtime_substate=None,
    )
    repo = _FakeReconciliationQueryRepo([candidate])
    uow = _FakeReconciliationUoW()
    inspector = _FakeInspector(
        {
            session_id: RuntimeInspectorResult(
                session_id=session_id,
                requested_runtime_id="runtime-1",
                matched_runtime_ids=("runtime-1", "runtime-2", "runtime-3"),
                exists=True,
                duplicate_count=2,
                phase="Running",
                ready=True,
                reason=None,
            )
        }
    )

    result = process_reconciliation_once(
        session_query_repo=repo,
        uow=uow,  # type: ignore[arg-type]
        inspector=inspector,  # type: ignore[arg-type]
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    enqueued_runtime_ids = [x["runtime_id"] for x in uow.outbox.cleanup_enqueues]
    assert enqueued_runtime_ids == ["runtime-2", "runtime-3"]


def test_process_reconciliation_once_phase_failed_transitions_runtime_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = uuid4()
    candidate = ReconciliationCandidate(
        state="ACTIVE",
        session_id=session_id,
        runtime_id="runtime-1",
        runtime_substate=None,
    )
    repo = _FakeReconciliationQueryRepo([candidate])
    uow = _FakeReconciliationUoW()
    inspector = _FakeInspector(
        {
            session_id: RuntimeInspectorResult(
                session_id=session_id,
                requested_runtime_id="runtime-1",
                matched_runtime_ids=("runtime-1",),
                exists=True,
                duplicate_count=0,
                phase="Failed",
                ready=False,
                reason="CrashLoopBackOff",
            )
        }
    )
    calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        orchestrator_service, "transition_session", _fake_transition_session
    )

    result = process_reconciliation_once(
        session_query_repo=repo,
        uow=uow,  # type: ignore[arg-type]
        inspector=inspector,  # type: ignore[arg-type]
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert len(calls) == 1
    assert calls[0]["trigger"] == Trigger.RUNTIME_FAILED


def test_process_expiry_once_provisioning_timeout_transitions_expired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = uuid4()
    now = datetime.now(timezone.utc)
    repo = _FakeExpiryQueryRepo(
        [
            ExpiryCandidate(
                state="PROVISIONING",
                session_id=session_id,
                created_at=now - timedelta(minutes=20),
                started_at=None,
                ended_at=None,
            )
        ]
    )

    calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        orchestrator_service, "transition_session", _fake_transition_session
    )

    result = process_expiry_once(
        session_query_repo=repo,
        uow=object(),  # type: ignore[arg-type]
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert len(calls) == 1
    assert calls[0]["trigger"] == Trigger.PROVISIONING_MAX_TIME
    assert calls[0]["session_id"] == session_id


def test_process_expiry_once_max_lifetime_transitions_expired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = uuid4()
    now = datetime.now(timezone.utc)
    repo = _FakeExpiryQueryRepo(
        [
            ExpiryCandidate(
                state="ACTIVE",
                session_id=session_id,
                created_at=now - timedelta(days=2),
                started_at=now - timedelta(days=2),
                ended_at=None,
            )
        ]
    )

    calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        orchestrator_service, "transition_session", _fake_transition_session
    )

    result = process_expiry_once(
        session_query_repo=repo,
        uow=object(),  # type: ignore[arg-type]
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert len(calls) == 1
    assert calls[0]["trigger"] == Trigger.SESSION_MAX_TIME
    assert calls[0]["session_id"] == session_id


def test_process_expiry_once_non_expired_no_transition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = uuid4()
    now = datetime.now(timezone.utc)
    repo = _FakeExpiryQueryRepo(
        [
            ExpiryCandidate(
                state="ACTIVE",
                session_id=session_id,
                created_at=now - timedelta(minutes=1),
                started_at=now - timedelta(minutes=1),
                ended_at=None,
            )
        ]
    )

    calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        orchestrator_service, "transition_session", _fake_transition_session
    )

    result = process_expiry_once(
        session_query_repo=repo,
        uow=object(),  # type: ignore[arg-type]
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert len(calls) == 0


def test_process_expiry_once_transition_failure_continues(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(timezone.utc)
    first_id = uuid4()
    second_id = uuid4()
    repo = _FakeExpiryQueryRepo(
        [
            ExpiryCandidate(
                state="PROVISIONING",
                session_id=first_id,
                created_at=now - timedelta(minutes=20),
                started_at=None,
                ended_at=None,
            ),
            ExpiryCandidate(
                state="PROVISIONING",
                session_id=second_id,
                created_at=now - timedelta(minutes=20),
                started_at=None,
                ended_at=None,
            ),
        ]
    )

    calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        calls.append(kwargs)
        if kwargs["session_id"] == first_id:
            raise RuntimeError("simulated transition failure")
        return object()

    monkeypatch.setattr(
        orchestrator_service, "transition_session", _fake_transition_session
    )

    result = process_expiry_once(
        session_query_repo=repo,
        uow=object(),  # type: ignore[arg-type]
    )

    assert result.claimed_count == 2
    assert result.succeeded_count == 1
    assert result.failed_count == 1
    assert len(calls) == 2
