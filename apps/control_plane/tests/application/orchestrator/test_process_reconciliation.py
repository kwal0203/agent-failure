from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
import apps.control_plane.src.application.orchestrator.service as orchestrator_service

from apps.control_plane.src.application.orchestrator.service import (
    process_reconciliation_once,
)
from apps.control_plane.src.application.orchestrator.types import (
    ReconciliationCandidate,
    RuntimeInspectorRequest,
    RuntimeInspectorResult,
)
from apps.control_plane.src.application.trace.types import TraceEvent
from apps.control_plane.src.domain.session_lifecycle.state_machine import Trigger


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


class _FakeReconciliationQueryRepo:
    def __init__(self, sessions: list[ReconciliationCandidate]) -> None:
        self._sessions = sessions

    def get_reconciliation_candidates(
        self, *, limit: int = 100
    ) -> list[ReconciliationCandidate]:
        _ = limit
        return self._sessions


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
        inspector=inspector,
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
        inspector=inspector,
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
        inspector=inspector,
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
        inspector=inspector,
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert len(calls) == 1
    assert calls[0]["trigger"] == Trigger.RUNTIME_FAILED


def test_process_reconciliation_once_active_with_missing_runtime_id_transitions_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = uuid4()
    candidate = ReconciliationCandidate(
        state="ACTIVE",
        session_id=session_id,
        runtime_id=None,
        runtime_substate=None,
    )
    repo = _FakeReconciliationQueryRepo([candidate])
    uow = _FakeReconciliationUoW()
    inspector = _FakeInspector({})

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
        inspector=inspector,
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert result.failed_count == 0
    assert len(calls) == 1
    assert calls[0]["trigger"] == Trigger.RUNTIME_FAILED
    assert calls[0]["metadata"]["reason_code"] == "MISSING_RUNTIME_ID"
