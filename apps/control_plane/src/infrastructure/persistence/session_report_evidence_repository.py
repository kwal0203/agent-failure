from uuid import UUID
from typing import cast

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from apps.control_plane.src.application.session_report_evidence.ports import (
    SessionReportEvidenceRepositoryPort,
)
from apps.control_plane.src.application.session_report_evidence.types import (
    SessionReportEvidenceItemInput,
    TraceEvidencePriority,
    TraceEvidenceType,
    SessionReportEvidenceRow,
)

from .models import SessionModel, SessionReportEvidenceModel


class SQLAlchemySessionReportEvidenceRepository(SessionReportEvidenceRepositoryPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_session_owner_user_id(self, *, session_id: UUID) -> UUID | None:
        stmt = select(SessionModel.owner_user_id).where(SessionModel.id == session_id)
        return self._db.execute(stmt).scalar_one_or_none()

    def list_report_evidence_for_session(
        self, *, session_id: UUID
    ) -> list[SessionReportEvidenceRow]:
        rows = (
            self._db.execute(
                select(SessionReportEvidenceModel)
                .where(SessionReportEvidenceModel.session_id == session_id)
                .order_by(
                    SessionReportEvidenceModel.position.asc(),
                    SessionReportEvidenceModel.created_at.asc(),
                    SessionReportEvidenceModel.id.asc(),
                )
            )
            .scalars()
            .all()
        )
        return [
            SessionReportEvidenceRow(
                id=row.id,
                session_id=row.session_id,
                event_id=row.event_id,
                position=row.position,
                title=row.title,
                description=row.description,
                occurred_at=row.occurred_at,
                evidence_type=cast(TraceEvidenceType, row.evidence_type),
                objective_keys=tuple(row.objective_keys),
                why_it_matters=row.why_it_matters,
                default_priority=cast(TraceEvidencePriority, row.default_priority),
                student_note=row.student_note,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]

    def replace_report_evidence_for_session(
        self,
        *,
        session_id: UUID,
        items: list[SessionReportEvidenceItemInput],
    ) -> None:
        self._db.execute(
            delete(SessionReportEvidenceModel).where(
                SessionReportEvidenceModel.session_id == session_id
            )
        )
        for item in items:
            self._db.add(
                SessionReportEvidenceModel(
                    session_id=session_id,
                    event_id=item.event_id,
                    position=item.position,
                    title=item.title,
                    description=item.description,
                    occurred_at=item.occurred_at,
                    evidence_type=item.evidence_type,
                    objective_keys=list(item.objective_keys),
                    why_it_matters=item.why_it_matters,
                    default_priority=item.default_priority,
                    student_note=item.student_note,
                )
            )

    # Convenience aliases matching planning shorthand.
    def list_by_session(self, *, session_id: UUID) -> list[SessionReportEvidenceRow]:
        return self.list_report_evidence_for_session(session_id=session_id)

    def replace_for_session(
        self, *, session_id: UUID, items: list[SessionReportEvidenceItemInput]
    ) -> None:
        self.replace_report_evidence_for_session(session_id=session_id, items=items)
