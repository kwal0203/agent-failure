from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from apps.control_plane.src.application.session_objectives.ports import (
    LabObjectiveTemplateReaderPort,
    SessionObjectiveWriterPort,
)

from .models import LabObjectivesModel, SessionObjectiveModel


class SQLAlchemyLabObjectiveTemplateRepository(LabObjectiveTemplateReaderPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_objective_templates(
        self, lab_version_id: UUID
    ) -> list[tuple[str, str, int]]:
        stmt = (
            select(
                LabObjectivesModel.objective_key,
                LabObjectivesModel.label,
                LabObjectivesModel.sort_order,
            )
            .where(LabObjectivesModel.lab_version_id == lab_version_id)
            .order_by(LabObjectivesModel.sort_order.asc())
        )
        rows = self._db.execute(stmt).all()
        return [(row.objective_key, row.label, row.sort_order) for row in rows]


class SQLAlchemySessionObjectiveWriterRepository(SessionObjectiveWriterPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def upsert_objective(
        self,
        session_id: UUID,
        objective_key: str,
        label: str,
        sort_order: int,
    ) -> None:
        stmt = insert(SessionObjectiveModel).values(
            session_id=session_id,
            objective_key=objective_key,
            label=label,
            status="pending",
            sort_order=sort_order,
            completed_at=None,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_session_objective_key",
            set_={
                "label": stmt.excluded.label,
                "sort_order": stmt.excluded.sort_order,
                # Preserve complete/pending state; this path only materializes templates.
                "updated_at": func.now(),
            },
        )
        self._db.execute(stmt)

    def mark_complete(
        self,
        *,
        session_id: UUID,
        objective_key: str,
        completed_at: datetime | None = None,
    ) -> None:
        row = (
            self._db.execute(
                select(SessionObjectiveModel).where(
                    SessionObjectiveModel.session_id == session_id,
                    SessionObjectiveModel.objective_key == objective_key,
                )
            )
            .scalars()
            .one_or_none()
        )
        if row is None:
            return
        if row.status == "complete":
            return

        row.status = "complete"
        row.completed_at = completed_at or datetime.now(timezone.utc)
        row.updated_at = datetime.now(timezone.utc)
