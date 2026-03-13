from typing import Protocol
from uuid import UUID
from dataclasses import dataclass
from .schemas import CreateSessionResult


@dataclass(frozen=True)
class AdmissionDecision:
    allowed: bool
    code: str | None
    message: str | None
    retryable: bool
    details: dict[str, object] | None


class LabRepository(Protocol):
    def validate_lab(self, lab_id: UUID) -> bool: ...


class AdmissionPolicy(Protocol):
    def check_launch_allowed(
        self, user_id: UUID, lab_id: UUID
    ) -> AdmissionDecision: ...


class CreateSessionRepository(Protocol):
    def create_provision_session(
        self, lab_id: UUID, actor_id: UUID, actor_role: str
    ) -> CreateSessionResult: ...
