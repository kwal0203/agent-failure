from fastapi import FastAPI, Depends, Request, Header
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from uuid import UUID
from .schemas import (
    GetSessionMetadataResponse,
    SessionMetadataResponse,
    ApiErrorEnvelope,
    ApiError,
    CreateSessionResponse,
    SessionResponse,
    CreateSessionRequest,
)
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionMetadataRepository,
)
from apps.control_plane.src.application.session_create.service import create_session
from apps.control_plane.src.application.session_query.service import (
    get_session_metadata,
)
from apps.control_plane.src.application.session_create.ports import (
    AdmissionPolicy,
    CreateSessionRepository,
    LabRepository,
)

from apps.control_plane.src.application.session_create.types import PrincipalContext
from apps.control_plane.src.application.session_create.schemas import (
    CreateSessionResult,
)

from sqlalchemy.orm import Session
from collections.abc import AsyncIterator
from apps.control_plane.src.application.common.ports import IdempotencyStore

from .auth import Principal, get_current_principal, UnauthenticatedError
from .dependencies import (
    get_admission_policy,
    get_idempotency_store,
    get_lab_repository,
    get_session_repository,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(lifespan=lifespan)


@app.exception_handler(UnauthenticatedError)
async def handle_unauthenticated(
    request: Request, exc: UnauthenticatedError
) -> JSONResponse:
    body = ApiErrorEnvelope(
        error=ApiError(
            code="UNAUTHENTICATED",
            message="Missing or invalid bearer token",
            retryable=False,
            details=None,
        )
    )
    return JSONResponse(content=body.model_dump(mode="json"), status_code=401)


@app.get(
    "/api/v1/sessions/{session_id}",
    response_model=GetSessionMetadataResponse,
    responses={404: {"model": ApiErrorEnvelope}},
)
def get_metadata(
    session_id: UUID, db: Session = Depends(get_db_session)
) -> GetSessionMetadataResponse | JSONResponse:
    repo = SQLAlchemySessionMetadataRepository(db=db)
    session_metadata = get_session_metadata(session_id=session_id, repo=repo)
    if session_metadata is None:
        error_body = ApiError(
            code="SESSION_NOT_FOUND",
            message="Session not found",
            retryable=False,
            details={"session_id": str(session_id)},
        )
        error_envelope = ApiErrorEnvelope(error=error_body)
        return JSONResponse(
            status_code=404, content=error_envelope.model_dump(mode="json")
        )

    http_obj = SessionMetadataResponse(
        id=session_metadata.id,
        lab_id=session_metadata.lab_id,
        lab_version_id=session_metadata.lab_version_id,
        state=session_metadata.state,
        runtime_substate=session_metadata.runtime_substate,
        resume_mode=session_metadata.resume_mode,
        interactive=session_metadata.interactive,
        created_at=session_metadata.created_at,
        started_at=session_metadata.started_at,
        ended_at=session_metadata.ended_at,
    )
    return GetSessionMetadataResponse(session=http_obj)


@app.post("/api/v1/sessions", response_model=CreateSessionResponse, status_code=202)
def create_session_endpoint(
    request: CreateSessionRequest,
    principal: Principal = Depends(get_current_principal),
    lab_repo: LabRepository = Depends(get_lab_repository),
    admission_policy: AdmissionPolicy = Depends(get_admission_policy),
    idempotency_store: IdempotencyStore[CreateSessionResult] = Depends(
        get_idempotency_store
    ),
    sessions: CreateSessionRepository = Depends(get_session_repository),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> CreateSessionResponse | JSONResponse | None:
    # TODO: Spec alignment: Idempotency-Key is opaque. Refactor downstream
    # app/persistence types to str for idempotency keys (currently UUID-based).

    # Idempotency key validity check
    key = idempotency_key.strip()
    if not key or len(key) > 128:
        body = ApiErrorEnvelope(
            error=ApiError(
                code="INVALID_IDEMPOTENCY_KEY",
                message="Valid Idempotency-Key header is required",
                retryable=False,
                details=None,
            )
        )
        return JSONResponse(status_code=400, content=body.model_dump(mode="json"))

    application_principal = PrincipalContext(
        user_id=principal.user_id, role=principal.role
    )
    result = create_session(
        principal=application_principal,
        admission_policy=admission_policy,
        lab_repo=lab_repo,
        sessions=sessions,
        idempotency_store=idempotency_store,
        lab_id=request.lab_id,
        idempotency_key=key,
    )

    session = SessionResponse(
        id=result.session_id,
        lab_id=result.lab_id,
        lab_version_id=result.lab_version_id,
        state=result.state,
        resume_mode=result.resume_mode,
        created_at=result.created_at,
    )
    return CreateSessionResponse(session=session)
