from datetime import datetime, timezone
from typing import cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from apps.control_plane.src.application.session_hints.ports import (
    LabHintTemplateReaderPort,
    SessionHintProjectorPort,
    SessionHintSeenPort,
    SessionHintWriterPort,
)
from apps.control_plane.src.application.session_hints.types import (
    DueSessionHint,
    HintTemplate,
)

from .models import LabHintTemplateModel, SessionHintModel, SessionModel


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


class SQLAlchemySessionHintProjectorRepository(SessionHintProjectorPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def claim_due_pending_hints(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[DueSessionHint]:
        ts = now or datetime.now(timezone.utc)
        stmt = (
            select(SessionHintModel)
            .where(
                SessionHintModel.status == "pending",
                SessionHintModel.unlock_at <= ts,
            )
            .order_by(
                SessionHintModel.unlock_at.asc(), SessionHintModel.sort_order.asc()
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        rows = self._db.execute(stmt).scalars().all()
        return [
            DueSessionHint(
                session_id=row.session_id,
                hint_key=row.hint_key,
                text=row.text,
                sort_order=row.sort_order,
                unlock_at=row.unlock_at,
            )
            for row in rows
        ]

    def mark_unlocked(
        self,
        *,
        session_id: UUID,
        hint_key: str,
        unlocked_at: datetime | None = None,
    ) -> bool:
        ts = unlocked_at or datetime.now(timezone.utc)
        stmt = (
            update(SessionHintModel)
            .where(
                SessionHintModel.session_id == session_id,
                SessionHintModel.hint_key == hint_key,
                SessionHintModel.status == "pending",
            )
            .values(status="unlocked", unlocked_at=ts, updated_at=func.now())
        )
        result = cast(CursorResult[object], self._db.execute(stmt))
        rowcount = result.rowcount or 0
        return rowcount > 0


class SQLAlchemySessionHintSeenRepository(SessionHintSeenPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_session_owner_user_id(self, *, session_id: UUID) -> UUID | None:
        stmt = select(SessionModel.owner_user_id).where(SessionModel.id == session_id)
        return self._db.execute(stmt).scalars().one_or_none()

    def mark_all_unlocked_seen(
        self,
        *,
        session_id: UUID,
        seen_at: datetime,
    ) -> int:
        stmt = (
            update(SessionHintModel)
            .where(
                SessionHintModel.session_id == session_id,
                SessionHintModel.status == "unlocked",
                SessionHintModel.seen_at.is_(None),
            )
            .values(seen_at=seen_at, updated_at=func.now())
        )
        result = cast(CursorResult[object], self._db.execute(stmt))
        return result.rowcount or 0
