"""Ports for session email injection workflow."""

from typing import Protocol
from uuid import UUID
from datetime import datetime

from apps.control_plane.src.application.orchestrator.types import SessionRuntimeBinding
from apps.control_plane.src.application.session_query.ports import (
    SessionMetadataRepository,
)
from apps.control_plane.src.application.trace.ports import (
    TraceEventPort,
    TraceOutboxPort,
)


class RuntimeBindingReaderPort(Protocol):
    def get_by_session_id(
        self, *, session_id: UUID
    ) -> SessionRuntimeBinding | None: ...


class SessionObjectiveStatusPort(Protocol):
    def is_malicious_email_injected_complete(self, *, session_id: UUID) -> bool: ...


class SessionEmailOutboxPort(TraceOutboxPort, Protocol):
    def enqueue_session_objective_completed(
        self,
        *,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        objective_key: str,
        reason_code: str,
        trigger_event_index: int,
        idempotency_key: str,
        source: str,
        evaluator_version: int | None,
        occurred_at: datetime,
    ) -> None: ...


class SessionEmailTransactionPort(Protocol):
    def commit(self) -> None: ...


class SessionEmailDeps(Protocol):
    @property
    def metadata_repo(self) -> SessionMetadataRepository: ...

    @property
    def runtime_binding_repo(self) -> RuntimeBindingReaderPort: ...

    @property
    def trace_repo(self) -> TraceEventPort: ...

    @property
    def outbox_repo(self) -> SessionEmailOutboxPort: ...

    @property
    def objective_status(self) -> SessionObjectiveStatusPort: ...

    @property
    def tx(self) -> SessionEmailTransactionPort: ...
