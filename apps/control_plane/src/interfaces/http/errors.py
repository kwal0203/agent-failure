from fastapi.responses import JSONResponse

from apps.control_plane.src.interfaces.http.helpers import build_api_error_response


def api_error(
    *,
    code: str,
    message: str,
    status_code: int,
    retryable: bool = False,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    return build_api_error_response(
        code=code,
        message=message,
        retryable=retryable,
        status_code=status_code,
        details=details,
    )


def forbidden(message: str, details: dict[str, object] | None = None) -> JSONResponse:
    return api_error(
        code="FORBIDDEN",
        message=message,
        status_code=403,
        retryable=False,
        details=details,
    )


def internal_error(
    message: str = "unexpected server error",
    *,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    return api_error(
        code="INTERNAL_ERROR",
        message=message,
        status_code=500,
        retryable=False,
        details=details,
    )


def session_not_found(session_id: str) -> JSONResponse:
    return api_error(
        code="SESSION_NOT_FOUND",
        message="Session not found",
        status_code=404,
        retryable=False,
        details={"session_id": session_id},
    )
