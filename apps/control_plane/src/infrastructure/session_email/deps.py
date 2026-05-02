"""Infrastructure adapters for session email service dependencies."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.control_plane.src.infrastructure.persistence.models import (
    SessionObjectiveModel,
)
from apps.control_plane.src.infrastructure.persistence.outbox import SQLAlchemyOutbox
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionMetadataRepository,
    SQLAlchemySessionRuntimeBindingRepository,
    SQLAlchemyTraceEventRepository,
)


class SessionEmailObjectiveStatus:
    def __init__(self, *, db: Session):
        self._db = db

    def is_malicious_email_injected_complete(self, *, session_id: UUID) -> bool:
        objective = (
            self._db.execute(
                select(SessionObjectiveModel).where(
                    SessionObjectiveModel.session_id == session_id,
                    SessionObjectiveModel.objective_key == "malicious_email_injected",
                )
            )
            .scalars()
            .one_or_none()
        )
        return bool(objective is not None and objective.status == "complete")


class SessionEmailDeps:
    def __init__(self, *, db: Session):
        self.metadata_repo = SQLAlchemySessionMetadataRepository(db=db)
        self.runtime_binding_repo = SQLAlchemySessionRuntimeBindingRepository(db=db)
        self.trace_repo = SQLAlchemyTraceEventRepository(db=db)
        self.outbox_repo = SQLAlchemyOutbox(db=db)
        self.objective_status = SessionEmailObjectiveStatus(db=db)
        self.tx = db


def build_session_email_deps(*, db: Session) -> SessionEmailDeps:
    return SessionEmailDeps(db=db)
