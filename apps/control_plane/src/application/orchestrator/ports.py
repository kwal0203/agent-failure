from typing import Protocol, ContextManager
from datetime import datetime
from uuid import UUID
from apps.control_plane.src.application.session_lifecycle.ports import UnitOfWork
from apps.control_plane.src.application.session_create.ports import LabRepository
from apps.control_plane.src.application.trace.ports import TraceEventPort
from apps.control_plane.src.application.session_objectives.ports import (
    LabObjectiveTemplateReaderPort,
    SessionObjectiveWriterPort,
)
from apps.control_plane.src.application.session_hints.ports import (
    LabHintTemplateReaderPort,
    SessionHintWriterPort,
)

from .types import (
    ProvisionResult,
    RuntimeProvisionRequest,
    PendingProvisioningEvent,
    PendingCleanupEvent,
    RuntimeTeardownRequest,
    RuntimeTeardownResult,
    RuntimeInspectorRequest,
    RuntimeInspectorResult,
    ReconciliationCandidate,
    ExpiryCandidate,
    UpsertSessionRuntimeBindingInput,
)


class RuntimeProvisionerPort(Protocol):
    def provision(self, request: RuntimeProvisionRequest) -> ProvisionResult: ...


class RuntimeImageResolverPort(Protocol):
    def resolve(self, lab_slug: str, lab_version: str) -> str: ...


class SessionRuntimeBindingPort(Protocol):
    def upsert_runtime_binding(
        self, *, input: UpsertSessionRuntimeBindingInput
    ) -> None: ...


class OutboxProvisioningSessionPort(Protocol):
    def claim_pending_provisioning(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingProvisioningEvent]: ...

    def mark_processed(
        self, *, outbox_event_id: UUID, processed_at: datetime | None = None
    ) -> None: ...

    def mark_retryable_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        backoff_seconds: int = 15,
        failed_at: datetime | None = None,
    ) -> None: ...

    def mark_terminal_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        failed_at: datetime | None = None,
    ) -> None: ...


class OutboxCleanupSessionPort(Protocol):
    def claim_pending_cleanup(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingCleanupEvent]: ...

    def mark_processed(
        self, *, outbox_event_id: UUID, processed_at: datetime | None = None
    ) -> None: ...

    def mark_retryable_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        backoff_seconds: int = 15,
        failed_at: datetime | None = None,
    ) -> None: ...

    def mark_terminal_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        failed_at: datetime | None = None,
    ) -> None: ...


class RuntimeInspectorPort(Protocol):
    def inspect(self, request: RuntimeInspectorRequest) -> RuntimeInspectorResult: ...


class ProcessPendingOnceUnitOfWork(Protocol):
    @property
    def outbox(self) -> OutboxProvisioningSessionPort: ...

    @property
    def lifecycle_uow(self) -> UnitOfWork: ...

    @property
    def lab(self) -> LabRepository: ...

    @property
    def trace(self) -> TraceEventPort: ...

    @property
    def runtime_binding(self) -> SessionRuntimeBindingPort: ...

    @property
    def objective_templates(self) -> LabObjectiveTemplateReaderPort: ...

    @property
    def session_objectives(self) -> SessionObjectiveWriterPort: ...

    @property
    def hint_templates(self) -> LabHintTemplateReaderPort: ...

    @property
    def session_hints(self) -> SessionHintWriterPort: ...

    def transaction(self) -> ContextManager[None]: ...


class ProcessCleanupOnceUnitOfWork(Protocol):
    @property
    def outbox(self) -> OutboxCleanupSessionPort: ...

    @property
    def lifecycle_uow(self) -> UnitOfWork: ...

    def transaction(self) -> ContextManager[None]: ...


class RuntimeTeardownPort(Protocol):
    def teardown(self, request: RuntimeTeardownRequest) -> RuntimeTeardownResult: ...

    def resources_exist(self, session_id: str) -> bool: ...


class ReconciliationSessionQueryPort(Protocol):
    def get_reconciliation_candidates(
        self, *, limit: int = 100
    ) -> list[ReconciliationCandidate]: ...


class ExpirySessionPort(Protocol):
    def get_expiry_candidates(self, *, limit: int = 100) -> list[ExpiryCandidate]: ...
