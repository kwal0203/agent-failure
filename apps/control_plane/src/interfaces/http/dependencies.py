from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status

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
from apps.control_plane.src.application.runtime.types import RuntimeClientConfig
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
from apps.control_plane.src.application.runtime.ports import RuntimeClientPort
from apps.control_plane.src.infrastructure.runtime.client import RuntimeHttpClient


import os


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


def get_runtime_client_config() -> RuntimeClientConfig:
    base_url = os.getenv("RUNTIME_BASE_URL", "").strip()
    timeout_raw = os.getenv("RUNTIME_TIMEOUT_SECONDS", "").strip()
    auth_token = os.getenv("RUNTIME_AUTH_TOKEN", "").strip()

    if not base_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="runtime client base url not set",
        )

    try:
        timeout_seconds = float(timeout_raw)
    except ValueError:
        timeout_seconds = 10.0

    return RuntimeClientConfig(
        base_url=base_url,
        timeout_seconds=timeout_seconds,
        auth_token=auth_token or None,
    )


def get_runtime_client(
    config: RuntimeClientConfig = Depends(get_runtime_client_config),
) -> RuntimeClientPort:
    return RuntimeHttpClient(config=config)
