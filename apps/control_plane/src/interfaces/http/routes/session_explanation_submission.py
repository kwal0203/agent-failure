"""HTTP route for learner explanation submission."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from apps.contracts.src.schemas import ApiErrorEnvelope
from apps.control_plane.src.application.common.errors import (
    DuplicateIdempotencyKeyError,
)
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.learner_explanation.errors import (
    InvalidLearnerExplanationError,
)
from apps.control_plane.src.application.session_explanation_submission.service import (
    SessionExplanationPolicyError,
    SubmitLearnerExplanationCommand,
    submit_learner_explanation,
)
from apps.control_plane.src.application.session_query.errors import (
    ForbiddenErrorSessionQuery,
)
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.learner_explanation_repository import (
    LearnerExplanationRepository,
)
from apps.control_plane.src.infrastructure.persistence.outbox import SQLAlchemyOutbox
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionMetadataRepository,
    SQLAlchemyTraceEventRepository,
)
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.errors import (
    api_error,
    forbidden,
    session_not_found,
)
from apps.control_plane.src.interfaces.http.schemas import (
    LearnerExplanationRequest,
    LearnerExplanationResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class _SessionExplanationDeps:
    def __init__(self, *, db: Session):
        self.metadata_repo = SQLAlchemySessionMetadataRepository(db=db)
        self.learner_explanation_repo = LearnerExplanationRepository(db=db)
        self.trace_repo = SQLAlchemyTraceEventRepository(db=db)
        self.outbox = SQLAlchemyOutbox(db=db)


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
    db: Session = Depends(get_db_session),
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
                "lab_difficulty": None,
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
            deps=_SessionExplanationDeps(db=db),
        )
        if result is None:
            return session_not_found(str(session_id))
        return LearnerExplanationResponse(
            session_id=session_id,
            explanation_id=result.explanation_id,
            accepted=True,
        )
    except SessionExplanationPolicyError as exc:
        return api_error(
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            status_code=exc.status_code,
            details=exc.details,
        )
    except InvalidLearnerExplanationError as exc:
        return api_error(
            code=exc.code,
            message=exc.message,
            retryable=False,
            status_code=400,
            details=exc.details,
        )
    except ForbiddenErrorSessionQuery as exc:
        return forbidden(exc.message, exc.details)
    except ValidationError:
        return api_error(
            code="SESSION_METADATA_INVALID",
            message="Invalid lab difficulty on session_metadata",
            retryable=False,
            status_code=500,
            details={"session_id": str(session_id)},
        )
    except DuplicateIdempotencyKeyError as exc:
        return api_error(
            code=exc.code,
            message=exc.message,
            retryable=False,
            status_code=500,
            details=exc.details,
        )
    except Exception:
        logger.exception("learner explanation endpoint failed")
        return api_error(
            code="INTERNAL_SERVER_ERROR",
            message="Unknown error in explanation endpoint",
            retryable=False,
            status_code=500,
            details={"session_id": str(session_id)},
        )
