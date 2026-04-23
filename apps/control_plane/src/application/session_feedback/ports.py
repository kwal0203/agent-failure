from datetime import datetime
from typing import Protocol
from uuid import UUID

from .types import SessionFeedbackCreateInput, SessionFeedbackRow


class SessionFeedbackRepositoryPort(Protocol):
    def insert_feedback_if_absent(self, *, input: SessionFeedbackCreateInput) -> bool:
        """
        Insert feedback once by idempotency key.
        Returns True only when a new row was inserted.
        """
        ...

    def list_feedback_for_session(
        self, *, session_id: UUID
    ) -> list[SessionFeedbackRow]:
        """
        Return feedback rows for a session in deterministic display order.
        """
        ...

    def count_unread_feedback(self, *, session_id: UUID) -> int:
        """
        Count unread feedback rows for a session.
        """
        ...

    def mark_feedback_read(
        self,
        *,
        session_id: UUID,
        feedback_id: UUID,
        seen_at: datetime,
    ) -> bool:
        """
        Mark a single feedback row read exactly once.
        Returns True only if a row transitioned from unread -> read.
        """
        ...

    def mark_all_feedback_read(self, *, session_id: UUID, seen_at: datetime) -> int:
        """
        Mark all unread feedback rows as read for a session.
        Returns number of rows updated.
        """
        ...
