"""Infrastructure adapters for session explanation submission dependencies."""

from sqlalchemy.orm import Session

from apps.control_plane.src.infrastructure.persistence.learner_explanation_repository import (
    LearnerExplanationRepository,
)
from apps.control_plane.src.infrastructure.persistence.outbox import SQLAlchemyOutbox
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionMetadataRepository,
    SQLAlchemyTraceEventRepository,
)


class SessionExplanationDeps:
    def __init__(self, *, db: Session):
        self.metadata_repo = SQLAlchemySessionMetadataRepository(db=db)
        self.learner_explanation_repo = LearnerExplanationRepository(db=db)
        self.trace_repo = SQLAlchemyTraceEventRepository(db=db)
        self.outbox = SQLAlchemyOutbox(db=db)


def build_session_explanation_deps(*, db: Session) -> SessionExplanationDeps:
    return SessionExplanationDeps(db=db)
