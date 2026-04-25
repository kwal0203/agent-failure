from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from apps.control_plane.src.application.session_feedback.ports import (
    SessionFeedbackRepositoryPort,
)
from apps.control_plane.src.application.session_feedback.types import (
    FeedbackSeverity,
    SessionFeedbackCreateInput,
    SessionFeedbackRow,
)

from .models import SessionFeedbackModel
from .models import SessionModel
from .session_feedback_ordering import session_feedback_ordering


class SQLAlchemySessionFeedbackRepository(SessionFeedbackRepositoryPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_session_owner_user_id(self, *, session_id: UUID) -> UUID | None:
        stmt = select(SessionModel.owner_user_id).where(SessionModel.id == session_id)
        return self._db.execute(stmt).scalar_one_or_none()

    def insert_feedback_if_absent(self, *, input: SessionFeedbackCreateInput) -> bool:
        stmt = insert(SessionFeedbackModel).values(
            session_id=input.session_id,
            feedback_key=input.feedback_key,
            reason_code=input.reason_code,
            message=input.message,
            severity=input.severity,
            trigger_event_index=input.trigger_event_index,
            created_at=input.created_at,
            seen_at=None,
            idempotency_key=input.idempotency_key,
        )
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_session_feedback_idempotency_key"
        )
        returning_stmt = stmt.returning(SessionFeedbackModel.id)
        inserted_id = self._db.execute(returning_stmt).scalar_one_or_none()
        return inserted_id is not None

    def list_feedback_for_session(
        self, *, session_id: UUID
    ) -> list[SessionFeedbackRow]:
        rows = (
            self._db.execute(
                select(SessionFeedbackModel)
                .where(SessionFeedbackModel.session_id == session_id)
                .order_by(*session_feedback_ordering())
            )
            .scalars()
            .all()
        )
        return [
            SessionFeedbackRow(
                id=row.id,
                session_id=row.session_id,
                feedback_key=row.feedback_key,
                reason_code=row.reason_code,
                message=row.message,
                severity=cast(FeedbackSeverity, row.severity),
                trigger_event_index=row.trigger_event_index,
                created_at=row.created_at,
                seen_at=row.seen_at,
                idempotency_key=row.idempotency_key,
            )
            for row in rows
        ]

    def count_unread_feedback(self, *, session_id: UUID) -> int:
        count = self._db.execute(
            select(func.count(SessionFeedbackModel.id)).where(
                SessionFeedbackModel.session_id == session_id,
                SessionFeedbackModel.seen_at.is_(None),
            )
        ).scalar_one()
        return int(count)

    def mark_feedback_read(
        self,
        *,
        session_id: UUID,
        feedback_id: UUID,
        seen_at: datetime,
    ) -> bool:
        stmt = (
            update(SessionFeedbackModel)
            .where(
                SessionFeedbackModel.id == feedback_id,
                SessionFeedbackModel.session_id == session_id,
                SessionFeedbackModel.seen_at.is_(None),
            )
            .values(seen_at=seen_at, updated_at=func.now())
        )
        result = cast(CursorResult[object], self._db.execute(stmt))
        rowcount = result.rowcount or 0
        return rowcount > 0

    def mark_all_feedback_read(self, *, session_id: UUID, seen_at: datetime) -> int:
        stmt = (
            update(SessionFeedbackModel)
            .where(
                SessionFeedbackModel.session_id == session_id,
                SessionFeedbackModel.seen_at.is_(None),
            )
            .values(seen_at=seen_at, updated_at=func.now())
        )
        result = cast(CursorResult[object], self._db.execute(stmt))
        return result.rowcount or 0
