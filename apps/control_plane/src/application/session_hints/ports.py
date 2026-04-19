from datetime import datetime
from typing import Protocol
from uuid import UUID

from .types import HintTemplate


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
