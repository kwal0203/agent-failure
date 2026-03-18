from typing import Protocol, ContextManager
from uuid import UUID
from dataclasses import dataclass
from datetime import datetime
from apps.control_plane.src.application.common.ports import IdempotencyStore

from .schemas import CreateSessionResult
from .types import LabRuntimeBinding


@dataclass(frozen=True)
class AdmissionDecision:
    allowed: bool
    code: str | None
    message: str | None
    retryable: bool
    details: dict[str, object] | None


class AdmissionPolicy(Protocol):
    def check_launch_allowed(
        self, user_id: UUID, lab_id: UUID
    ) -> AdmissionDecision: ...


class CreateSessionRepository(Protocol):
    def create_provision_session(
        self, lab_id: UUID, actor_id: UUID, actor_role: str
    ) -> CreateSessionResult: ...


class OutboxCreateSession(Protocol):
    def enqueue_for_session_creation(
        self,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID | None,
        lab_slug: str,
        lab_version: str,
        resume_mode: str,
        requester_user_id: UUID,
        idempotency_key: str,
        requested_at: datetime | None,
    ) -> None: ...


class LabRepository(Protocol):
    def validate_lab(self, lab_id: UUID) -> bool: ...
    def get_runtime_binding(
        self, lab_id: UUID, lab_version_id: UUID
    ) -> LabRuntimeBinding: ...


class CreateSessionUnitOfWork(Protocol):
    @property
    def sessions(self) -> CreateSessionRepository: ...

    @property
    def idempotency(self) -> IdempotencyStore[CreateSessionResult]: ...

    @property
    def outbox(self) -> OutboxCreateSession: ...

    @property
    def lab_repo(self) -> LabRepository: ...

    def transaction(self) -> ContextManager[None]: ...
