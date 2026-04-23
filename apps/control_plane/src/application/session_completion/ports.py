from datetime import datetime
from typing import Protocol
from uuid import UUID

from .types import (
    CompletionStatus,
    PendingSessionCompletedEvent,
    SessionCompletionState,
)


class OutboxSessionCompletedPort(Protocol):
    def claim_pending_session_completed(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingSessionCompletedEvent]: ...

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


class SessionCompletionWriterPort(Protocol):
    def get_completion_state(
        self, *, session_id: UUID
    ) -> SessionCompletionState | None: ...

    def mark_completion_if_in_progress(
        self,
        *,
        session_id: UUID,
        completion_status: CompletionStatus,
        completed_at: datetime,
        completion_reason_code: str | None,
    ) -> bool: ...
