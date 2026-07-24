from dataclasses import dataclass
from uuid import UUID
from typing import Literal, Mapping, Any
from datetime import datetime


RuntimeBindingStatus = Literal["provisioning", "ready", "failed", "terminated"]
RuntimeKind = Literal["k8s_pod"]
RUNTIME_BINDING_STATUSES: tuple[RuntimeBindingStatus, ...] = (
    "provisioning",
    "ready",
    "failed",
    "terminated",
)
RUNTIME_KINDS: tuple[RuntimeKind, ...] = ("k8s_pod",)


@dataclass(frozen=True)
class RuntimeProvisionRequest:
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    image_ref: str
    metadata: Mapping[str, object]


@dataclass(frozen=True)
class ProvisionResult:
    status: Literal["accepted", "ready", "failed"]
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


@dataclass(frozen=True)
class ProcessCleanupOnceResult:
    claimed_count: int
    succeeded_count: int
    failed_count: int
    retried_count: int


@dataclass(frozen=True)
class RuntimeTeardownRequest:
    session_id: UUID
    runtime_id: str | None = None
    metadata: Mapping[str, object] | None = None


@dataclass(frozen=True)
class RuntimeTeardownResult:
    status: Literal["deleted", "already_gone", "failed"]
    reason_code: str | None = None
    details: dict[str, object] | None = None


@dataclass(frozen=True)
class RuntimeInspectorRequest:
    session_id: UUID
    runtime_id: str | None = None


@dataclass(frozen=True)
class RuntimeInspectorResult:
    session_id: UUID
    requested_runtime_id: str | None
    matched_runtime_ids: tuple[str, ...]
    exists: bool
    duplicate_count: int
    phase: str | None = None
    ready: bool | None = None
    reason: str | None = None
    details: dict[str, object] | None = None


@dataclass(frozen=True)
class ReconciliationCandidate:
    state: str
    session_id: UUID
    runtime_id: str | None
    runtime_substate: str | None


@dataclass(frozen=True)
class ReconciliationOnceResult:
    claimed_count: int
    succeeded_count: int
    failed_count: int
    retried_count: int


@dataclass(frozen=True)
class ExpiryCandidate:
    state: str
    session_id: UUID
    created_at: datetime
    started_at: datetime | None = None
    ended_at: datetime | None = None


@dataclass(frozen=True)
class ExpiryOnceResult:
    claimed_count: int
    succeeded_count: int
    failed_count: int
    retried_count: int


@dataclass(frozen=True)
class UpsertSessionRuntimeBindingInput:
    session_id: UUID
    runtime_kind: RuntimeKind
    base_url: str | None
    auth_token_ref: str | None = None
    status: RuntimeBindingStatus = "provisioning"
    last_error: str | None = None

    def __post_init__(self) -> None:
        if self.status == "ready" and (
            self.base_url is None or not self.base_url.strip()
        ):
            raise ValueError("A ready runtime binding requires a base URL")


@dataclass(frozen=True)
class SessionRuntimeBinding:
    session_id: UUID
    runtime_kind: RuntimeKind
    base_url: str | None
    auth_token_ref: str | None
    status: RuntimeBindingStatus | None = None
    last_error: str | None = None
