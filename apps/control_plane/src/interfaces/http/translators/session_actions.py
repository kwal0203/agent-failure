"""Translate session action domain errors into HTTP responses."""

from uuid import UUID

from fastapi.responses import JSONResponse

from apps.control_plane.src.application.session_feedback.errors import (
    ForbiddenErrorSessionFeedback,
    SessionNotFoundErrorSessionFeedback,
)
from apps.control_plane.src.application.session_hints.errors import (
    ForbiddenErrorSessionHints,
    SessionNotFoundErrorSessionHints,
)
from apps.control_plane.src.application.session_lifecycle.errors import (
    InvalidTransition,
)
from apps.control_plane.src.application.session_query.errors import (
    ForbiddenErrorSessionQuery,
)
from apps.control_plane.src.interfaces.http.errors import (
    api_error,
    forbidden,
    internal_error,
)


def translate_stop_session_error(exc: Exception, *, session_id: UUID) -> JSONResponse:
    if isinstance(exc, ForbiddenErrorSessionQuery):
        return forbidden(exc.message, exc.details)
    if isinstance(exc, InvalidTransition):
        return api_error(
            code="INVALID_SESSION_STATE",
            message="Session cannot be stopped from the current state",
            retryable=False,
            status_code=409,
            details={
                "session_id": str(session_id),
                "current_state": exc.current_state.value,
                "trigger": exc.trigger.value,
            },
        )
    return internal_error(
        "Unexpected server error", details={"session_id": str(session_id)}
    )


def translate_mark_hints_seen_error(
    exc: Exception, *, session_id: UUID
) -> JSONResponse:
    if isinstance(exc, ForbiddenErrorSessionHints):
        return forbidden(exc.message, exc.details)
    if isinstance(exc, SessionNotFoundErrorSessionHints):
        return api_error(
            code="SESSION_NOT_FOUND",
            message="Session not found",
            retryable=False,
            status_code=404,
            details={"session_id": str(session_id), "exists": False},
        )
    return internal_error(
        "Unexpected server error", details={"session_id": str(session_id)}
    )


def translate_mark_feedback_seen_error(
    exc: Exception, *, session_id: UUID
) -> JSONResponse:
    if isinstance(exc, ForbiddenErrorSessionFeedback):
        return forbidden(exc.message, exc.details)
    if isinstance(exc, SessionNotFoundErrorSessionFeedback):
        return api_error(
            code="SESSION_NOT_FOUND",
            message="Session not found",
            retryable=False,
            status_code=404,
            details={"session_id": str(session_id), "exists": False},
        )
    return internal_error(
        "Unexpected server error", details={"session_id": str(session_id)}
    )
