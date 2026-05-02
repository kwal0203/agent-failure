"""HTTP routes for session evaluator feedback and trace queries."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from apps.contracts.src.schemas import (
    ApiErrorEnvelope,
    GetFeedbackResponse,
    GetSessionTraceResponse,
)
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.evaluator_feedback.service import (
    get_session_evaluator_feedback,
)
from apps.control_plane.src.application.evaluator_feedback.ports import EvaluatorPort
from apps.control_plane.src.application.session_query.ports import (
    SessionMetadataRepository,
)
from apps.control_plane.src.application.session_query.service import (
    get_session_metadata,
)
from apps.control_plane.src.application.trace.service import (
    project_learner_visible_events,
)
from apps.control_plane.src.application.trace.ports import TraceEventPort
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.dependencies import (
    get_evaluator_repository,
    get_session_metadata_repository,
    get_trace_event_repository,
)
from apps.control_plane.src.interfaces.http.error_mapping import (
    map_exception_to_http_response,
    map_unexpected_exception,
)
from apps.control_plane.src.interfaces.http.errors import session_not_found
from apps.control_plane.src.interfaces.http.mappers.session_mapper import (
    map_evaluator_feedback_response,
    map_session_trace_response,
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
    repo: EvaluatorPort = Depends(get_evaluator_repository),
) -> GetFeedbackResponse | JSONResponse:
    try:
        evaluator_feedback_item = get_session_evaluator_feedback(
            principal=principal, session_id=session_id, repo=repo
        )
        return map_evaluator_feedback_response(evaluator_feedback_item)

    except Exception as exc:
        mapped = map_exception_to_http_response(exc, session_id=session_id)
        if mapped is not None:
            return mapped
        logger.exception(
            "get evaluator feedback endpoint failed for session=%s", str(session_id)
        )
        return map_unexpected_exception(session_id=session_id)


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
    repo: TraceEventPort = Depends(get_trace_event_repository),
    metadata_repo: SessionMetadataRepository = Depends(get_session_metadata_repository),
) -> GetSessionTraceResponse | JSONResponse:
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

    except Exception as exc:
        mapped = map_exception_to_http_response(exc, session_id=session_id)
        if mapped is not None:
            return mapped
        logger.exception(
            "get session trace endpoint failed for session=%s", str(session_id)
        )
        return map_unexpected_exception(session_id=session_id)
