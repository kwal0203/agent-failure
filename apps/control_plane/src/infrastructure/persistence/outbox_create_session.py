from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from apps.control_plane.src.application.session_create.ports import OutboxCreateSession

from .models import OutboxEventModel


class SQLAlchemyOutboxCreateSession(OutboxCreateSession):
    def __init__(self, db: Session) -> None:
        self._db = db

    def enqueue_for_session_creation(
        self,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID | None,
        lab_slug: str,
        lab_version: str,
        resume_mode: str,
        requester_user_id: UUID,
        idempotency_key: str,
        requested_at: datetime | None,
    ) -> None:
        payload: dict[str, object] = {
            "session_id": str(session_id),
            "lab_id": str(lab_id),
            "lab_version_id": str(lab_version_id)
            if lab_version_id is not None
            else None,
            "lab_slug": lab_slug,
            "lab_version": lab_version,
            "resume_mode": resume_mode,
            "requester_user_id": str(requester_user_id),
            "idempotency_key": str(idempotency_key),
            "requested_at": requested_at.isoformat()
            if requested_at is not None
            else None,
        }

        event = OutboxEventModel(
            event_type="session.provisioning.v1",
            aggregate_id=session_id,
            payload=payload,
        )
        self._db.add(event)
