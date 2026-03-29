from uuid import UUID
from typing import Protocol, ContextManager
from .schemas import TransitionResult
from dataclasses import dataclass
from apps.control_plane.src.domain.session_lifecycle.state_machine import (
    SessionState,
    Trigger,
)
from apps.control_plane.src.application.common.ports import IdempotencyStore
from apps.control_plane.src.application.trace.ports import TraceEventPort
from typing import Mapping
from datetime import datetime


@dataclass
class SessionRow:
    id: UUID
    runtime_id: str | None
    state: SessionState


class SessionRepository(Protocol):
    def get_for_update(self, session_id: UUID) -> SessionRow | None: ...

    def update_state(
        self,
        session_id: UUID,
        from_state: SessionState,
        to_state: SessionState,
        actor: str,
        reason: str | None,
    ) -> None: ...

    def insert_transition_event(
        self,
        session_id: UUID,
        prev_state: SessionState,
        next_state: SessionState,
        trigger: Trigger,
        actor: str,
        metadata: Mapping[str, object],
        idempotency_key: str,
    ) -> TransitionResult: ...


class Outbox(Protocol):
    def enqueue_for_transition(
        self,
        session_id: UUID,
        prev_state: SessionState,
        next_state: SessionState,
        trigger: Trigger,
        metadata: Mapping[str, object],
        transition_id: UUID,
    ) -> None: ...

    def enqueue_for_cleanup(
        self,
        session_id: UUID,
        runtime_id: str | None,
        terminal_state: str | None,
        reason_code: str | None,
        requested_at: datetime | None,
    ) -> None: ...

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
    ) -> None: ...


class UnitOfWork(Protocol):
    @property
    def sessions(self) -> SessionRepository: ...

    @property
    def idempotency(self) -> IdempotencyStore[TransitionResult]: ...

    @property
    def outbox(self) -> Outbox: ...

    @property
    def trace(self) -> TraceEventPort: ...

    def transaction(self) -> ContextManager[None]: ...
