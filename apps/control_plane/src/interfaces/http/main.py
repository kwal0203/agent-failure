from fastapi import FastAPI, Depends, Header
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from uuid import UUID
from .schemas import (
    GetSessionMetadataResponse,
    SessionMetadataResponse,
    ApiErrorEnvelope,
    ApiError,
    CreateSessionResponse,
    CreateSessionRequest,
)
from sqlalchemy.orm import Session
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionMetadataRepository,
)
from apps.control_plane.src.application.session_query.service import (
    get_session_metadata,
)
from collections.abc import AsyncIterator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(lifespan=lifespan)


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
def create_session(
    request: CreateSessionRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    authorization: str = Header(..., alias="Authorization"),
    db: Session = Depends(get_db_session),
) -> CreateSessionResponse | JSONResponse | None:
    # TODO: Spec alignment: Idempotency-Key is opaque. Refactor downstream
    # app/persistence types to str for idempotency keys (currently UUID-based).
    # Creates a new session for a published lab.

    if not authorization.startswith("Bearer "):
        error_body = ApiError(
            code="UNAUTHENTICATED",
            message="Missing or invalid bearer token",
            retryable=False,
            details=None,
        )
        error_envelope = ApiErrorEnvelope(error=error_body)
        return JSONResponse(
            content=error_envelope.model_dump(mode="json"), status_code=401
        )

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        error_body = ApiError(
            code="UNAUTHENTICATED",
            message="Missing or invalid bearer token",
            retryable=False,
            details=None,
        )
        error_envelope = ApiErrorEnvelope(error=error_body)
        return JSONResponse(
            content=error_envelope.model_dump(mode="json"), status_code=401
        )

    key = idempotency_key.strip()
    if not key:
        error_body = ApiError(
            code="INVALID_IDEMPOTENCY_KEY",
            message="Valid Idempotency-Key header is required",
            retryable=False,
            details=None,
        )
        error_envelope = ApiErrorEnvelope(error=error_body)
        return JSONResponse(
            content=error_envelope.model_dump(mode="json"), status_code=400
        )

    if len(key) > 128:
        error_body = ApiError(
            code="INVALID_IDEMPOTENCY_KEY",
            message="Idempotency-Key is too long",
            retryable=False,
            details=None,
        )
        error_envelope = ApiErrorEnvelope(error=error_body)
        return JSONResponse(
            content=error_envelope.model_dump(mode="json"), status_code=400
        )

    return None

    # - authenticated learner or admin acting as a learner in future-supported workflows

    # - validates lab availability

    # - validates quota and degraded-mode restrictions
    # - creates a durable session row if the idempotency key has not been used

    # - returns the existing session if the same idempotency key is replayed for the same logical request
