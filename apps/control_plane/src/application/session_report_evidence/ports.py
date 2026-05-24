from typing import Protocol
from uuid import UUID

from .types import (
    SessionReportDraftSections,
    SessionReportEvidenceItemInput,
    SessionReportEvidenceRow,
)


class SessionReportEvidenceRepositoryPort(Protocol):
    def get_session_owner_user_id(self, *, session_id: UUID) -> UUID | None:
        """
        Return owning user id for session, or None when session does not exist.
        """
        ...

    def list_report_evidence_for_session(
        self, *, session_id: UUID
    ) -> list[SessionReportEvidenceRow]:
        """
        Return persisted report evidence rows in deterministic order.
        """
        ...

    def replace_report_evidence_for_session(
        self,
        *,
        session_id: UUID,
        items: list[SessionReportEvidenceItemInput],
    ) -> None:
        """
        Full-replace report evidence rows for a session in one transaction.
        """
        ...


class SessionReportDraftRepositoryPort(Protocol):
    def get_report_draft_sections_for_session(
        self, *, session_id: UUID
    ) -> SessionReportDraftSections | None:
        """
        Return stored report draft sections for a session, or None if absent.
        """
        ...

    def upsert_report_draft_sections_for_session(
        self, *, session_id: UUID, sections: SessionReportDraftSections
    ) -> None:
        """
        Create or update report draft sections for a session.
        """
        ...
