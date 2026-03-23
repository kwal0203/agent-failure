from sqlalchemy.orm import Session
from fastapi import Depends

from apps.control_plane.src.application.session_create.ports import (
    AdmissionPolicy,
    LabRepository,
    CreateSessionRepository,
    CreateSessionUnitOfWork,
)
from apps.control_plane.src.application.session_create.schemas import (
    CreateSessionResult,
)
from apps.control_plane.src.application.common.ports import IdempotencyStore
from apps.control_plane.src.infrastructure.policy.admission import StubAdmissionPolicy
from apps.control_plane.src.infrastructure.persistence.lab_repository import (
    SQLAlchemyLabRepository,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemyCreateSessionRepository,
    SQLAlchemySessionMetadataRepository,
)
from apps.control_plane.src.application.session_query.ports import (
    SessionMetadataRepository,
)
from apps.control_plane.src.infrastructure.persistence.db import (
    get_db_session,
    SessionFactory,
)
from apps.control_plane.src.infrastructure.persistence.idempotency_store import (
    SQLAlchemyCreateSessionIdempotencyStore,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work_create_session import (
    SQLAlchemyCreateSessionUnitOfWork,
)


class AdmissionPolicyStub:
    pass


def get_admission_policy() -> AdmissionPolicy:
    return StubAdmissionPolicy()


def get_idempotency_store(
    db: Session = Depends(get_db_session),
) -> IdempotencyStore[CreateSessionResult]:
    return SQLAlchemyCreateSessionIdempotencyStore(db=db)


def get_lab_repository(db: Session = Depends(get_db_session)) -> LabRepository:
    return SQLAlchemyLabRepository(db=db)


def get_session_repository(
    db: Session = Depends(get_db_session),
) -> CreateSessionRepository:
    return SQLAlchemyCreateSessionRepository(db=db)


def get_create_session_uow() -> CreateSessionUnitOfWork:
    return SQLAlchemyCreateSessionUnitOfWork(session_factory=SessionFactory)


def get_session_metadata_repository(
    db: Session = Depends(get_db_session),
) -> SessionMetadataRepository:
    return SQLAlchemySessionMetadataRepository(db=db)
