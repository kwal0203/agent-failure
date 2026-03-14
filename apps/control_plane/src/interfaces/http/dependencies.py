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
    PostgresLabRepository,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    PostgresCreateSessionRepository,
)
from apps.control_plane.src.infrastructure.persistence.db import (
    get_db_session,
    SessionFactory,
)
from apps.control_plane.src.infrastructure.persistence.idempotency_store import (
    PostgresCreateSessionIdempotencyStore,
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
    return PostgresCreateSessionIdempotencyStore(db=db)


def get_lab_repository(db: Session = Depends(get_db_session)) -> LabRepository:
    return PostgresLabRepository(db=db)


def get_session_repository(
    db: Session = Depends(get_db_session),
) -> CreateSessionRepository:
    return PostgresCreateSessionRepository(db=db)


def get_create_session_uow() -> CreateSessionUnitOfWork:
    return SQLAlchemyCreateSessionUnitOfWork(session_factory=SessionFactory)
