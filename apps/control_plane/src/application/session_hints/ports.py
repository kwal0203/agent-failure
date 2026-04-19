from datetime import datetime
from typing import Protocol
from uuid import UUID

from .types import DueSessionHint, HintTemplate


class LabHintTemplateReaderPort(Protocol):
    def list_hint_templates(self, lab_version_id: UUID) -> list[HintTemplate]:
        """
        Return active hint templates for a lab version in display/unlock order.
        """
        ...


class SessionHintWriterPort(Protocol):
    def upsert_hint(
        self,
        *,
        session_id: UUID,
        hint_key: str,
        text: str,
        sort_order: int,
        unlock_at: datetime,
    ) -> None:
        """
        Ensure a session hint exists for (session_id, hint_key) with pending semantics.
        Intended to be idempotent for repeated calls.
        """
        ...


class SessionHintProjectorPort(Protocol):
    def claim_due_pending_hints(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[DueSessionHint]:
        """
        Claim due hints that are still pending.
        Implementations should use lock-safe claim semantics for workers.
        """
        ...

    def mark_unlocked(
        self,
        *,
        session_id: UUID,
        hint_key: str,
        unlocked_at: datetime | None = None,
    ) -> bool:
        """
        Transition a hint from pending -> unlocked exactly once.
        Returns True only when a state change occurred.
        """
        ...


class OutboxSessionHintUnlockedPort(Protocol):
    def enqueue_session_hint_unlocked(
        self,
        *,
        session_id: UUID,
        hint_key: str,
        text: str,
        sort_order: int,
        unlocked_at: datetime,
        idempotency_key: str,
    ) -> None: ...
