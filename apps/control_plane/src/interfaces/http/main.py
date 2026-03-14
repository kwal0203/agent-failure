from fastapi import FastAPI, Depends, Request, Header
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from uuid import UUID
from .schemas import (
    GetSessionMetadataResponse,
    SessionMetadataResponse,
    ApiErrorEnvelope,
    ApiError,
    SessionResponse,
    CreateSessionResponse,
    CreateSessionRequest,
)
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionMetadataRepository,
)
from apps.control_plane.src.application.session_query.service import (
    get_session_metadata,
)
from apps.control_plane.src.application.session_query.errors import (
    ForbiddenErrorSessionQuery,
)
from apps.control_plane.src.application.session_create.ports import (
    AdmissionPolicy,
    CreateSessionUnitOfWork,
)

from apps.control_plane.src.application.session_create.types import PrincipalContext
from apps.control_plane.src.application.session_create.service import create_session
from apps.control_plane.src.application.session_create.errors import (
    LabNotAvailableError,
    QuotaExceededError,
    RateLimitedError,
    DegradedModeRestrictionError,
    InvalidIdempotencyKeyError,
    ForbiddenError,
    AdmissionDecisionError,
)

from sqlalchemy.orm import Session
from collections.abc import AsyncIterator

from .auth import Principal, get_current_principal, UnauthenticatedError
from .dependencies import get_admission_policy, get_create_session_uow


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
    session_id: UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db_session),
) -> GetSessionMetadataResponse | JSONResponse:
    repo = SQLAlchemySessionMetadataRepository(db=db)

    try:
        session_metadata = get_session_metadata(
            session_id=session_id,
            principal_user_id=principal.user_id,
            principal_user_role=principal.role,
            repo=repo,
        )
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
    except ForbiddenErrorSessionQuery as exc:
        body = ApiErrorEnvelope(
            error=ApiError(
                code="FORBIDDEN",
                message=exc.message,
                retryable=False,
                details=exc.details,
            )
        )
        return JSONResponse(content=body.model_dump(mode="json"), status_code=403)


@app.post(
    "/api/v1/sessions",
    response_model=CreateSessionResponse,
    status_code=202,
    responses={
        400: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        404: {"model": ApiErrorEnvelope},
        429: {"model": ApiErrorEnvelope},
        503: {"model": ApiErrorEnvelope},
    },
)
def create_session_endpoint(
    request: CreateSessionRequest,
    principal: Principal = Depends(get_current_principal),
    admission_policy: AdmissionPolicy = Depends(get_admission_policy),
    uow: CreateSessionUnitOfWork = Depends(get_create_session_uow),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> CreateSessionResponse | JSONResponse | None:
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

    try:
        result = create_session(
            principal=application_principal,
            admission_policy=admission_policy,
            lab_id=request.lab_id,
            idempotency_key=key,
            uow=uow,
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
    except LabNotAvailableError as exc:
        body = ApiErrorEnvelope(
            error=ApiError(
                code="LAB_NOT_AVAILABLE",
                message=exc.message,
                retryable=False,
                details=exc.details,
            )
        )
        return JSONResponse(content=body.model_dump(mode="json"), status_code=404)
    except QuotaExceededError as exc:
        body = ApiErrorEnvelope(
            error=ApiError(
                code="QUOTA_EXCEEDED",
                message=exc.message,
                retryable=False,
                details=exc.details,
            )
        )
        return JSONResponse(content=body.model_dump(mode="json"), status_code=429)
    except RateLimitedError as exc:
        body = ApiErrorEnvelope(
            error=ApiError(
                code="RATE_LIMITED",
                message=exc.message,
                retryable=False,
                details=exc.details,
            )
        )
        return JSONResponse(content=body.model_dump(mode="json"), status_code=429)
    except DegradedModeRestrictionError as exc:
        body = ApiErrorEnvelope(
            error=ApiError(
                code="DEGRADED_MODE_RESTRICTION",
                message=exc.message,
                retryable=False,
                details=exc.details,
            )
        )
        return JSONResponse(content=body.model_dump(mode="json"), status_code=503)
    except InvalidIdempotencyKeyError as exc:
        body = ApiErrorEnvelope(
            error=ApiError(
                code="INVALID_IDEMPOTENCY_KEY",
                message=exc.message,
                retryable=False,
                details=exc.details,
            )
        )
        return JSONResponse(content=body.model_dump(mode="json"), status_code=400)
    except ForbiddenError as exc:
        body = ApiErrorEnvelope(
            error=ApiError(
                code="FORBIDDEN",
                message=exc.message,
                retryable=False,
                details=exc.details,
            )
        )
        return JSONResponse(content=body.model_dump(mode="json"), status_code=403)
    except AdmissionDecisionError as exc:
        body = ApiErrorEnvelope(
            error=ApiError(
                code="ADMISSION_DENIED",
                message=exc.message,
                retryable=False,
                details=exc.details,
            )
        )
        return JSONResponse(content=body.model_dump(mode="json"), status_code=400)
    except Exception:
        body = ApiErrorEnvelope(
            error=ApiError(
                code="INTERNAL_ERROR",
                message="unexpected server error.",
                retryable=False,
                details=None,
            )
        )
        return JSONResponse(content=body.model_dump(mode="json"), status_code=500)
