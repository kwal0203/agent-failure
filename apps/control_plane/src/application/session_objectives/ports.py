from datetime import datetime
from typing import Protocol
from uuid import UUID

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
