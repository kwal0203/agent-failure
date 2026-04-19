from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.control_plane.src.application.session_hints.ports import (
    LabHintTemplateReaderPort,
)
from apps.control_plane.src.application.session_hints.types import HintTemplate

from .models import LabHintTemplateModel


class SQLAlchemyLabHintTemplateRepository(LabHintTemplateReaderPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_hint_templates(self, lab_version_id: UUID) -> list[HintTemplate]:
        stmt = (
            select(
                LabHintTemplateModel.hint_key,
                LabHintTemplateModel.text,
                LabHintTemplateModel.offset_seconds,
                LabHintTemplateModel.sort_order,
            )
            .where(
                LabHintTemplateModel.lab_version_id == lab_version_id,
                LabHintTemplateModel.is_active.is_(True),
            )
            .order_by(LabHintTemplateModel.sort_order.asc())
        )
        rows = self._db.execute(stmt).all()
        return [
            HintTemplate(
                hint_key=row.hint_key,
                text=row.text,
                offset_seconds=row.offset_seconds,
                sort_order=row.sort_order,
            )
            for row in rows
        ]
