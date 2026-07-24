"""HTTP route for learner explanation submission."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.contracts.src.schemas import ApiErrorEnvelope
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.session_explanation_submission.service import (
    SubmitLearnerExplanationCommand,
    submit_learner_explanation,
)
from apps.control_plane.src.application.session_explanation_submission.ports import (
    SessionExplanationDeps,
)
from apps.control_plane.src.interfaces.http.dependencies import (
    get_request_db_session,
    get_session_explanation_deps,
)
from apps.control_plane.src.interfaces.http.error_mapping import (
    map_exception_to_http_response,
    map_unexpected_exception,
)
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.errors import (
    api_error,
    session_not_found,
)
from apps.control_plane.src.interfaces.http.schemas import (
    LearnerExplanationRequest,
    LearnerExplanationResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/api/v1/sessions/{session_id}/explanation",
    status_code=202,
    response_model=LearnerExplanationResponse,
    responses={
        400: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        404: {"model": ApiErrorEnvelope},
        409: {"model": ApiErrorEnvelope},
        500: {"model": ApiErrorEnvelope},
    },
)
def learner_explanation(
    session_id: UUID,
    request: LearnerExplanationRequest,
    principal: PrincipalContext = Depends(get_current_principal),
    deps: SessionExplanationDeps = Depends(get_session_explanation_deps),
    db: Session = Depends(get_request_db_session),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> LearnerExplanationResponse | JSONResponse:
    key = idempotency_key.strip()
    if not key or len(key) > 128:
        logger.warning(
            "invalid learner explanation idempotency key",
            extra={
                "event": "learner_explanation_invalid_idempotency_key",
                "session_id": str(session_id),
                "lab_id": None,
                "user_id": str(principal.user_id),
            },
        )
        return api_error(
            code="INVALID_IDEMPOTENCY_KEY",
            message="Valid Idempotency-Key header is required",
            retryable=False,
            status_code=400,
        )

    try:
        result = submit_learner_explanation(
            command=SubmitLearnerExplanationCommand(
                session_id=session_id,
                principal=principal,
                explanation=request.explanation,
                idempotency_key=key,
            ),
            deps=deps,
        )
        if result is None:
            return session_not_found(str(session_id))
        return LearnerExplanationResponse(
            session_id=session_id,
            explanation_id=result.explanation_id,
            accepted=True,
        )
    except Exception as exc:
        mapped = map_exception_to_http_response(exc, session_id=session_id)
        if mapped is not None:
            return mapped
        logger.exception("learner explanation endpoint failed")
        return map_unexpected_exception(session_id=session_id)
