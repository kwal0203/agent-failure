from fastapi.responses import JSONResponse

from .schemas import ApiError, ApiErrorEnvelope


def build_api_error_response(
    code: str,
    message: str,
    retryable: bool,
    status_code: int,
    details: dict[str, object] | None = None,
) -> JSONResponse:
    body = ApiErrorEnvelope(
        error=ApiError(code=code, message=message, retryable=retryable, details=details)
    )
    return JSONResponse(content=body.model_dump(mode="json"), status_code=status_code)
