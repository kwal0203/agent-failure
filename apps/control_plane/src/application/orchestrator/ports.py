from typing import Protocol
from datetime import datetime
from uuid import UUID

from .types import ProvisionResult, RuntimeProvisionRequest, PendingProvisioningEvent


class RuntimeProvisionerPort(Protocol):
    def provision(self, request: RuntimeProvisionRequest) -> ProvisionResult: ...


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
