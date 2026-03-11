from uuid import UUID
from typing import Protocol, ContextManager
from .schemas import TransitionResult
from dataclasses import dataclass
from apps.control_plane.src.domain.session_lifecycle.state_machine import (
    SessionState,
    Trigger,
)
from typing import Mapping


@dataclass
class SessionRow:
    id: UUID
    state: SessionState


class IdempotencyStore(Protocol):
    def get(self, key: UUID) -> TransitionResult | None: ...

    def save(self, key: UUID, result: TransitionResult) -> None: ...


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
        idempotency_key: UUID,
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


class UnitOfWork(Protocol):
    @property
    def sessions(self) -> SessionRepository: ...

    @property
    def idempotency(self) -> IdempotencyStore: ...

    @property
    def outbox(self) -> Outbox: ...

    def transaction(self) -> ContextManager[None]: ...
