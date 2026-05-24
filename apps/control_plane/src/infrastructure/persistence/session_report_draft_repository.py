from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.control_plane.src.application.session_report_evidence.ports import (
    SessionReportDraftRepositoryPort,
)
from apps.control_plane.src.application.session_report_evidence.types import (
    SessionReportDraftSections,
)

from .models import SessionReportDraftModel


class SQLAlchemySessionReportDraftRepository(SessionReportDraftRepositoryPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_report_draft_sections_for_session(
        self, *, session_id: UUID
    ) -> SessionReportDraftSections | None:
        row = self._db.execute(
            select(SessionReportDraftModel).where(
                SessionReportDraftModel.session_id == session_id
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return SessionReportDraftSections(
            executive_summary=row.executive_summary,
            threat_model=row.threat_model,
            methodology=row.methodology,
            evidence_and_results=row.evidence_and_results,
            mitigations=row.mitigations,
        )

    def upsert_report_draft_sections_for_session(
        self, *, session_id: UUID, sections: SessionReportDraftSections
    ) -> None:
        row = self._db.execute(
            select(SessionReportDraftModel).where(
                SessionReportDraftModel.session_id == session_id
            )
        ).scalar_one_or_none()

        if row is None:
            self._db.add(
                SessionReportDraftModel(
                    session_id=session_id,
                    executive_summary=sections.executive_summary,
                    threat_model=sections.threat_model,
                    methodology=sections.methodology,
                    evidence_and_results=sections.evidence_and_results,
                    mitigations=sections.mitigations,
                )
            )
        else:
            row.executive_summary = sections.executive_summary
            row.threat_model = sections.threat_model
            row.methodology = sections.methodology
            row.evidence_and_results = sections.evidence_and_results
            row.mitigations = sections.mitigations

        self._db.flush()
