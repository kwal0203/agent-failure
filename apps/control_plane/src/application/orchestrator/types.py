from dataclasses import dataclass
from uuid import UUID
from typing import Literal, Mapping, Any


Status = Literal["accepted", "ready", "failed"]


@dataclass(frozen=True)
class RuntimeProvisionRequest:
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    image_ref: str
    metadata: Mapping[str, object]


@dataclass(frozen=True)
class ProvisionResult:
    status: Status
    runtime_id: str | None = None
    reason_code: str | None = None
    details: dict[str, object] | None = None


@dataclass(frozen=True)
class PendingProvisioningEvent:
    outbox_event_id: UUID
    session_id: UUID
    payload: dict[str, Any]
    attempt_count: int


@dataclass(frozen=True)
class ProcessPendingOnceResult:
    claimed_count: int
    succeeded_count: int
    failed_count: int
    retried_count: int


@dataclass(frozen=True)
class PendingCleanupEvent:
    outbox_event_id: UUID
    session_id: UUID
    payload: dict[str, Any]
    attempt_count: int
