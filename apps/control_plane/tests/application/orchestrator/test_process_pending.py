from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
import apps.control_plane.src.application.orchestrator.service as orchestrator_service

from apps.control_plane.src.application.common.types import (
    GetLabCatalogRow,
    LabRuntimeBinding,
)
from apps.control_plane.src.application.orchestrator.service import process_pending_once
from apps.control_plane.src.application.orchestrator.types import (
    PendingProvisioningEvent,
    ProcessPendingOnceResult,
    ProvisionResult,
    RuntimeInspectorRequest,
    RuntimeInspectorResult,
    RuntimeProvisionRequest,
)
from apps.control_plane.src.application.session_lifecycle.ports import (
    SessionRow,
    UnitOfWork as SessionLifecycleUnitOfWork,
)
from apps.control_plane.src.application.session_hints.types import HintTemplate
from apps.control_plane.src.application.trace.types import TraceEvent
from apps.control_plane.src.domain.session_lifecycle.state_machine import (
    SessionState,
    Trigger,
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
        return LabRuntimeBinding(lab_slug="agent-prompt-injection", lab_version="v1")

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
    def __init__(self) -> None:
        self.cleanup_enqueues: list[dict[str, Any]] = []

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

    def enqueue_for_cleanup(
        self,
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


class _FakeLifecycleSessions:
    def __init__(
        self, state_by_session_id: dict[UUID, SessionState] | None = None
    ) -> None:
        self._state_by_session_id = state_by_session_id or {}

    def get_for_update(self, session_id: UUID) -> SessionRow | None:
        state = self._state_by_session_id.get(session_id, SessionState.PROVISIONING)
        return SessionRow(id=session_id, runtime_id=None, state=state)


class _FakeLifecycleUoW:
    def __init__(
        self, state_by_session_id: dict[UUID, SessionState] | None = None
    ) -> None:
        self._trace = _FakeTraceRepo()
        self._outbox = _FakeTraceOutbox()
        self._sessions = _FakeLifecycleSessions(state_by_session_id=state_by_session_id)

    @property
    def trace(self) -> _FakeTraceRepo:
        return self._trace

    @property
    def outbox(self) -> _FakeTraceOutbox:
        return self._outbox

    @property
    def sessions(self) -> _FakeLifecycleSessions:
        return self._sessions

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


class _FakeProcessPendingOnceUoW:
    def __init__(
        self,
        outbox: _FakeOutbox,
        *,
        lifecycle_state_by_session_id: dict[UUID, SessionState] | None = None,
    ) -> None:
        self._outbox = outbox
        self._lab = _FakeLabRepository()
        self._lifecycle_uow: SessionLifecycleUnitOfWork = _FakeLifecycleUoW(
            state_by_session_id=lifecycle_state_by_session_id
        )  # type: ignore[assignment]
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
    def runtime_binding(self) -> _FakeRuntimeBindingRepo:
        return self._runtime_binding

    @property
    def objective_templates(self) -> _FakeObjectiveTemplateRepo:
        return self._objective_templates

    @property
    def session_objectives(self) -> _FakeSessionObjectiveWriter:
        return self._session_objectives

    @property
    def hint_templates(self) -> _FakeHintTemplateRepo:
        return self._hint_templates

    @property
    def session_hints(self) -> _FakeSessionHintWriter:
        return self._session_hints

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


def _make_event(*, payload: dict[str, Any]) -> PendingProvisioningEvent:
    return PendingProvisioningEvent(
        outbox_event_id=uuid4(),
        session_id=uuid4(),
        payload=payload,
        attempt_count=0,
    )


def test_process_pending_once_success_marks_processed_and_transitions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ev = _make_event(
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


def test_process_pending_once_failed_provision_marks_terminal_and_transitions_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ev = _make_event(
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
    assert uow.runtime_binding.upsert_calls[0].base_url is None


def test_process_pending_once_missing_runtime_id_marks_terminal_and_transitions_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ev = _make_event(
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
            runtime_id=None,
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
    assert (
        outbox.terminal_calls[0].error_message
        == "Provisioning failed: MISSING_RUNTIME_ID"
    )
    assert len(transition_calls) == 1
    assert transition_calls[0]["trigger"] == Trigger.PROVISIONING_FAILED
    assert transition_calls[0]["session_id"] == ev.session_id


def test_process_pending_once_missing_base_url_fails_before_activation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ev = _make_event(
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
            details={},
        )
    )
    transition_calls: list[dict[str, Any]] = []

    def _fake_transition_session(**kwargs: Any) -> object:
        transition_calls.append(kwargs)
        return object()

    monkeypatch.setattr(
        orchestrator_service, "transition_session", _fake_transition_session
    )

    result = process_pending_once(
        uow=uow,
        image_resolver=_FakeResolver(),
        provisioner=provisioner,
        runtime_inspector=_FakeInspector(responses={}),
    )

    assert result == ProcessPendingOnceResult(
        claimed_count=1,
        succeeded_count=0,
        failed_count=1,
        retried_count=0,
    )
    assert len(outbox.processed_calls) == 0
    assert outbox.terminal_calls[0].error_message == (
        "Provisioning failed: MISSING_BASE_URL"
    )
    assert transition_calls[0]["trigger"] == Trigger.PROVISIONING_FAILED
    assert transition_calls[0]["metadata"]["reason_code"] == "MISSING_BASE_URL"


def test_process_pending_once_terminal_race_skips_activation_and_enqueues_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ev = _make_event(
        payload={
            "lab_id": str(uuid4()),
            "lab_version_id": str(uuid4()),
        }
    )
    outbox = _FakeOutbox(events=[ev])
    uow = _FakeProcessPendingOnceUoW(
        outbox=outbox,
        lifecycle_state_by_session_id={ev.session_id: SessionState.CANCELLED},
    )
    provisioner = _FakeProvisioner(
        result=ProvisionResult(
            status="accepted",
            runtime_id="r-terminal-race",
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
    assert len(transition_calls) == 0
    assert len(uow.lifecycle_uow.outbox.cleanup_enqueues) == 1  # type: ignore[attr-defined]
    cleanup = uow.lifecycle_uow.outbox.cleanup_enqueues[0]  # type: ignore[attr-defined]
    assert cleanup["session_id"] == ev.session_id
    assert cleanup["runtime_id"] == "r-terminal-race"
    assert cleanup["terminal_state"] == SessionState.CANCELLED.value
    assert cleanup["reason_code"] == "PROVISIONED_AFTER_TERMINAL"


def test_process_pending_once_malformed_payload_marks_terminal_and_skips_transition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ev = _make_event(
        payload={
            "lab_id": str(uuid4()),
            "lab_version_id": 123,
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
    ev = _make_event(
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
    ticks = iter([0.0, 0.0, 31.0])
    monkeypatch.setattr(orchestrator_service.time, "monotonic", lambda: next(ticks))

    def _no_sleep(seconds: float) -> None:
        pass

    monkeypatch.setattr(orchestrator_service.time, "sleep", _no_sleep)

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
