from uuid import UUID

from fastapi.responses import JSONResponse

from apps.control_plane.src.interfaces.http.error_mapping import (
    map_exception_to_http_response,
    map_unexpected_exception,
)


def translate_stop_session_error(exc: Exception, *, session_id: UUID) -> JSONResponse:
    return map_exception_to_http_response(
        exc, session_id=session_id
    ) or map_unexpected_exception(session_id=session_id)


def translate_mark_hints_seen_error(
    exc: Exception, *, session_id: UUID
) -> JSONResponse:
    return map_exception_to_http_response(
        exc, session_id=session_id
    ) or map_unexpected_exception(session_id=session_id)


def translate_mark_feedback_seen_error(
    exc: Exception, *, session_id: UUID
) -> JSONResponse:
    return map_exception_to_http_response(
        exc, session_id=session_id
    ) or map_unexpected_exception(session_id=session_id)
