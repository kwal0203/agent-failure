from apps.control_plane.src.application.session_create.ports import (
    AdmissionPolicy,
    CreateSessionRepository,
)
from apps.control_plane.src.application.session_create.schemas import (
    CreateSessionResult,
)
from apps.control_plane.src.application.common.ports import IdempotencyStore
from apps.control_plane.src.infrastructure.policy.admission import StubAdmissionPolicy
from apps.control_plane.src.application.session_create.ports import LabRepository
from apps.control_plane.src.infrastructure.persistence.lab_repository import (
    PostgresLabRepository,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    PostgresCreateSessionRepository,
)

from sqlalchemy.orm import Session
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from fastapi import Depends
from apps.control_plane.src.infrastructure.persistence.idempotency_store import (
    PostgresCreateSessionIdempotencyStore,
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
