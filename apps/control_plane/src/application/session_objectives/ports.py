from datetime import datetime
from typing import Protocol
from uuid import UUID

from apps.contracts.src.types import CompletionOutcome
from apps.control_plane.src.application.session_completion.types import CompletionStatus

from .types import PendingSessionObjectiveCompletedEvent


class LabObjectiveTemplateReaderPort(Protocol):
    def list_objective_templates(
        self, lab_version_id: UUID
    ) -> list[tuple[str, str, int]]:
        """
        Return objective templates for a lab version as:
        (objective_key, label, sort_order).
        """
        ...


class SessionObjectiveWriterPort(Protocol):
    def upsert_objective(
        self,
        session_id: UUID,
        objective_key: str,
        label: str,
        sort_order: int,
    ) -> None:
        """
        Ensure a session objective exists with pending status semantics.
        Intended to be idempotent for repeated calls.
        """
        ...

    def mark_complete(
        self,
        *,
        session_id: UUID,
        objective_key: str,
        completed_at: datetime | None = None,
    ) -> None: ...

    def list_objective_states(self, *, session_id: UUID) -> list[tuple[str, str]]: ...


class SessionCompletionWriterPort(Protocol):
    def mark_completion_if_in_progress(
        self,
        *,
        session_id: UUID,
        completion_status: CompletionStatus,
        completed_at: datetime,
        completion_reason_code: str | None,
    ) -> bool: ...


class SessionCompletionEventOutboxPort(Protocol):
    def enqueue_session_completed(
        self,
        *,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        outcome: CompletionOutcome,
        completion_reason_code: str | None,
        trigger_event_index: int | None,
        idempotency_key: str,
        occurred_at: datetime | None = None,
    ) -> None: ...


class OutboxSessionObjectiveCompletedPort(Protocol):
    def claim_pending_objective_completed(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingSessionObjectiveCompletedEvent]: ...

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
