from fastapi.responses import JSONResponse

from apps.control_plane.src.interfaces.http.error_mapping import (
    map_exception_to_http_response,
)


def translate_create_session_error(exc: Exception) -> JSONResponse:
    response = map_exception_to_http_response(exc)
    if response is None:
        raise TypeError(f"Unsupported create session error type: {type(exc)!r}")
    return response
