import logging

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from apps.contracts.src.schemas import ApiErrorEnvelope
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.session_create.ports import (
    AdmissionPolicy,
    CreateSessionUnitOfWork,
)
from apps.control_plane.src.application.session_create.service import create_session
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.dependencies import (
    get_admission_policy,
    get_create_session_uow,
)
from apps.control_plane.src.interfaces.http.errors import api_error, internal_error
from apps.control_plane.src.interfaces.http.schemas import (
    CreateSessionRequest,
    CreateSessionResponse,
    SessionResponse,
)
from apps.control_plane.src.interfaces.http.translators import (
    translate_create_session_error,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/api/v1/sessions",
    response_model=CreateSessionResponse,
    status_code=202,
    responses={
        400: {"model": ApiErrorEnvelope},
        401: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        404: {"model": ApiErrorEnvelope},
        429: {"model": ApiErrorEnvelope},
        500: {"model": ApiErrorEnvelope},
        503: {"model": ApiErrorEnvelope},
    },
)
def create_session_endpoint(
    request: CreateSessionRequest,
    principal: PrincipalContext = Depends(get_current_principal),
    admission_policy: AdmissionPolicy = Depends(get_admission_policy),
    uow: CreateSessionUnitOfWork = Depends(get_create_session_uow),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> CreateSessionResponse | JSONResponse | None:
    key = idempotency_key.strip()
    if not key or len(key) > 128:
        return api_error(
            code="INVALID_IDEMPOTENCY_KEY",
            message="Valid Idempotency-Key header is required",
            retryable=False,
            status_code=400,
        )

    application_principal = PrincipalContext(
        user_id=principal.user_id, role=principal.role
    )

    try:
        result = create_session(
            principal=application_principal,
            admission_policy=admission_policy,
            lab_id=request.lab_id,
            lab_difficulty=request.lab_difficulty,
            idempotency_key=key,
            uow=uow,
        )
        session = SessionResponse(
            id=result.session_id,
            lab_id=result.lab_id,
            lab_version_id=result.lab_version_id,
            lab_difficulty=result.lab_difficulty,
            state=result.state,
            resume_mode=result.resume_mode,
            created_at=result.created_at,
        )

        logger.info(
            "create session succeeded",
            extra={
                "event": "create_session_succeeded",
                "session_id": str(result.session_id),
                "lab_id": str(result.lab_id),
                "lab_version_id": str(result.lab_version_id)
                if result.lab_version_id is not None
                else None,
                "lab_difficulty": result.lab_difficulty,
                "user_id": str(application_principal.user_id),
            },
        )

        return CreateSessionResponse(session=session)
    except Exception as exc:
        try:
            return translate_create_session_error(exc)
        except TypeError:
            safe_idempo = f"{key[:8]}..." if key else None
            logger.exception(
                "create session endpoint failed",
                extra={
                    "event": "create_session_failed",
                    "lab_id": str(request.lab_id),
                    "lab_difficulty": request.lab_difficulty,
                    "user_id": str(application_principal.user_id),
                    "idempotency_key_prefix": safe_idempo,
                },
            )
            return internal_error()
