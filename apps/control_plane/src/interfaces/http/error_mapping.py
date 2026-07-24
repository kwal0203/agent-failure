"""Central exception-to-HTTP mapping for control-plane routes."""

from uuid import UUID

from fastapi.responses import JSONResponse

from apps.control_plane.src.application.errors import (
    AdmissionDecisionError,
    DegradedModeRestrictionError,
    DuplicateIdempotencyKeyError,
    ForbiddenError,
    ForbiddenErrorSessionFeedback,
    ForbiddenErrorSessionHints,
    ForbiddenErrorSessionQuery,
    ForbiddenErrorSessionReportEvidence,
    InvalidIdempotencyKeyError,
    InvalidLearnerExplanationError,
    InvalidSessionReportEvidenceError,
    InvalidTransition,
    LabNotAvailableError,
    QuotaExceededError,
    RateLimitedError,
    RuntimeClientError,
    SessionEmailPolicyError,
    SessionExplanationPolicyError,
    SessionNotFoundErrorSessionFeedback,
    SessionNotFoundErrorSessionHints,
    SessionNotFoundErrorSessionReportEvidence,
)
from apps.control_plane.src.interfaces.http.errors import (
    api_error,
    forbidden,
    internal_error,
)


def map_exception_to_http_response(
    exc: Exception, *, session_id: UUID | None = None
) -> JSONResponse | None:
    if isinstance(exc, (ForbiddenError, ForbiddenErrorSessionQuery)):
        return forbidden(exc.message, exc.details)
    if isinstance(
        exc,
        (
            ForbiddenErrorSessionHints,
            ForbiddenErrorSessionFeedback,
            ForbiddenErrorSessionReportEvidence,
        ),
    ):
        return forbidden(exc.message, exc.details)

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
    if isinstance(exc, AdmissionDecisionError):
        return api_error(
            code="ADMISSION_DENIED",
            message=exc.message,
            retryable=False,
            status_code=400,
            details=exc.details,
        )
    if isinstance(exc, InvalidTransition):
        details: dict[str, object] = {
            "current_state": exc.current_state.value,
            "trigger": exc.trigger.value,
        }
        if session_id is not None:
            details["session_id"] = str(session_id)
        return api_error(
            code="INVALID_SESSION_STATE",
            message="Session cannot be stopped from the current state",
            retryable=False,
            status_code=409,
            details=details,
        )
    if isinstance(
        exc,
        (
            SessionNotFoundErrorSessionHints,
            SessionNotFoundErrorSessionFeedback,
            SessionNotFoundErrorSessionReportEvidence,
        ),
    ):
        missing_details: dict[str, object] = {"exists": False}
        if session_id is not None:
            missing_details["session_id"] = str(session_id)
        return api_error(
            code="SESSION_NOT_FOUND",
            message="Session not found",
            retryable=False,
            status_code=404,
            details=missing_details,
        )
    if isinstance(exc, (SessionEmailPolicyError, SessionExplanationPolicyError)):
        return api_error(
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            status_code=exc.status_code,
            details=exc.details,
        )
    if isinstance(exc, InvalidSessionReportEvidenceError):
        return api_error(
            code="INVALID_REPORT_EVIDENCE",
            message=exc.message,
            retryable=False,
            status_code=400,
            details=exc.details,
        )
    if isinstance(exc, RuntimeClientError):
        runtime_details: dict[str, object] | None = (
            {"session_id": str(session_id)} if session_id is not None else None
        )
        return api_error(
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            status_code=502,
            details=runtime_details,
        )
    if isinstance(exc, InvalidLearnerExplanationError):
        return api_error(
            code=exc.code,
            message=exc.message,
            retryable=False,
            status_code=400,
            details=exc.details,
        )
    if isinstance(exc, DuplicateIdempotencyKeyError):
        return api_error(
            code=exc.code,
            message=exc.message,
            retryable=False,
            status_code=500,
            details=exc.details,
        )
    return None


def map_unexpected_exception(*, session_id: UUID | None = None) -> JSONResponse:
    details: dict[str, object] | None = (
        {"session_id": str(session_id)} if session_id is not None else None
    )
    return internal_error("Unexpected server error", details=details)
