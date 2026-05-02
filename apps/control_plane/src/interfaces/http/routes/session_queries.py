import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.contracts.src.schemas import ApiErrorEnvelope
from apps.control_plane.src.application.common.errors import ForbiddenError
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.evaluator_feedback.service import (
    get_session_evaluator_feedback,
)
from apps.control_plane.src.application.session_query.errors import (
    ForbiddenErrorSessionQuery,
)
from apps.control_plane.src.application.session_query.service import (
    get_session_metadata,
)
from apps.control_plane.src.application.trace.service import (
    project_learner_visible_events,
)
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemyEvaluatorRepository,
    SQLAlchemySessionMetadataRepository,
    SQLAlchemyTraceEventRepository,
)
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.errors import (
    forbidden,
    internal_error,
    session_not_found,
)
from apps.control_plane.src.interfaces.http.mappers.session_mapper import (
    map_evaluator_feedback_response,
    map_session_trace_response,
)
from apps.control_plane.src.interfaces.http.schemas import (
    GetFeedbackResponse,
    GetSessionTraceResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/api/v1/sessions/{session_id}/evaluator-feedback",
    response_model=GetFeedbackResponse,
    responses={
        401: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        500: {"model": ApiErrorEnvelope},
    },
)
def evaluator_feedback(
    session_id: UUID,
    principal: PrincipalContext = Depends(get_current_principal),
    db: Session = Depends(get_db_session),
) -> GetFeedbackResponse | JSONResponse:
    repo = SQLAlchemyEvaluatorRepository(db=db)

    try:
        evaluator_feedback_item = get_session_evaluator_feedback(
            principal=principal, session_id=session_id, repo=repo
        )
        return map_evaluator_feedback_response(evaluator_feedback_item)

    except ForbiddenError as exc:
        return forbidden(exc.message, exc.details)

    except Exception:
        logger.exception(
            "get evaluator feedback endpoint failed for session=%s", str(session_id)
        )
        return internal_error()


@router.get(
    "/api/v1/sessions/{session_id}/trace",
    response_model=GetSessionTraceResponse,
    responses={
        401: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        404: {"model": ApiErrorEnvelope},
        500: {"model": ApiErrorEnvelope},
    },
)
def get_session_trace(
    session_id: UUID,
    principal: PrincipalContext = Depends(get_current_principal),
    db: Session = Depends(get_db_session),
) -> GetSessionTraceResponse | JSONResponse:

    repo = SQLAlchemyTraceEventRepository(db=db)
    metadata_repo = SQLAlchemySessionMetadataRepository(db=db)

    try:
        session_metadata = get_session_metadata(
            session_id=session_id,
            principal=principal,
            repo=metadata_repo,
        )
        if session_metadata is None:
            return session_not_found(str(session_id))

        events = repo.list_trace_events_for_session(session_id=session_id)
        learner_events = project_learner_visible_events(events=events)

        return map_session_trace_response(learner_events)

    except ForbiddenErrorSessionQuery as exc:
        return forbidden(exc.message, exc.details)
    except Exception:
        logger.exception(
            "get session trace endpoint failed for session=%s", str(session_id)
        )
        return internal_error()
