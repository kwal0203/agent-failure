from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from apps.control_plane.src.application.session_hints.ports import (
    LabHintTemplateReaderPort,
    SessionHintWriterPort,
)
from apps.control_plane.src.application.session_hints.types import HintTemplate

from .models import LabHintTemplateModel, SessionHintModel


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


class SQLAlchemySessionHintWriterRepository(SessionHintWriterPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def upsert_hint(
        self,
        *,
        session_id: UUID,
        hint_key: str,
        text: str,
        sort_order: int,
        unlock_at: datetime,
    ) -> None:
        stmt = insert(SessionHintModel).values(
            session_id=session_id,
            hint_key=hint_key,
            text=text,
            sort_order=sort_order,
            unlock_at=unlock_at,
            status="pending",
            unlocked_at=None,
            seen_at=None,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_session_hints_session_key",
            set_={
                "text": stmt.excluded.text,
                "sort_order": stmt.excluded.sort_order,
                "unlock_at": stmt.excluded.unlock_at,
                # Preserve current unlock/seen lifecycle on replay.
                "updated_at": func.now(),
            },
        )
        self._db.execute(stmt)
