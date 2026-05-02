from fastapi.responses import JSONResponse

from apps.control_plane.src.application.common.errors import ForbiddenError
from apps.control_plane.src.application.session_create.errors import (
    AdmissionDecisionError,
    DegradedModeRestrictionError,
    InvalidIdempotencyKeyError,
    InvalidLabDifficulty,
    LabNotAvailableError,
    QuotaExceededError,
    RateLimitedError,
)
from apps.control_plane.src.interfaces.http.errors import api_error, forbidden


def translate_create_session_error(exc: Exception) -> JSONResponse:
    if isinstance(exc, LabNotAvailableError):
        return api_error(
            code="LAB_NOT_AVAILABLE",
            message=exc.message,
            retryable=False,
            status_code=404,
            details=exc.details,
        )
    if isinstance(exc, QuotaExceededError):
        return api_error(
            code="QUOTA_EXCEEDED",
            message=exc.message,
            retryable=False,
            status_code=429,
            details=exc.details,
        )
    if isinstance(exc, RateLimitedError):
        return api_error(
            code="RATE_LIMITED",
            message=exc.message,
            retryable=False,
            status_code=429,
            details=exc.details,
        )
    if isinstance(exc, DegradedModeRestrictionError):
        return api_error(
            code="DEGRADED_MODE_RESTRICTION",
            message=exc.message,
            retryable=False,
            status_code=503,
            details=exc.details,
        )
    if isinstance(exc, InvalidIdempotencyKeyError):
        return api_error(
            code="INVALID_IDEMPOTENCY_KEY",
            message=exc.message,
            retryable=False,
            status_code=400,
            details=exc.details,
        )
    if isinstance(exc, ForbiddenError):
        return forbidden(exc.message, exc.details)
    if isinstance(exc, AdmissionDecisionError):
        return api_error(
            code="ADMISSION_DENIED",
            message=exc.message,
            retryable=False,
            status_code=400,
            details=exc.details,
        )
    if isinstance(exc, InvalidLabDifficulty):
        return api_error(
            code="INVALID_LAB_DIFFICULTY",
            message=exc.message,
            retryable=False,
            status_code=400,
            details=exc.details,
        )
    raise TypeError(f"Unsupported create session error type: {type(exc)!r}")
