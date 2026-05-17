"""Central export surface for control-plane application/domain errors."""

from apps.control_plane.src.application.common.errors import (
    DuplicateIdempotencyKeyError,
    ForbiddenError,
)
from apps.control_plane.src.application.learner_explanation.errors import (
    InvalidLearnerExplanationError,
)
from apps.control_plane.src.application.runtime.errors import RuntimeClientError
from apps.control_plane.src.application.session_create.errors import (
    AdmissionDecisionError,
    DegradedModeRestrictionError,
    InvalidIdempotencyKeyError,
    InvalidLabDifficulty,
    LabNotAvailableError,
    QuotaExceededError,
    RateLimitedError,
)
from apps.control_plane.src.application.session_email.service import (
    SessionEmailPolicyError,
)
from apps.control_plane.src.application.session_explanation_submission.service import (
    SessionExplanationPolicyError,
)
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
    SessionNotFound,
)
from apps.control_plane.src.application.session_query.errors import (
    ForbiddenErrorSessionQuery,
)
from apps.control_plane.src.application.session_report_evidence.errors import (
    ForbiddenErrorSessionReportEvidence,
    InvalidSessionReportEvidenceError,
    SessionNotFoundErrorSessionReportEvidence,
)

__all__ = [
    "AdmissionDecisionError",
    "DegradedModeRestrictionError",
    "DuplicateIdempotencyKeyError",
    "ForbiddenError",
    "ForbiddenErrorSessionFeedback",
    "ForbiddenErrorSessionHints",
    "ForbiddenErrorSessionQuery",
    "ForbiddenErrorSessionReportEvidence",
    "InvalidIdempotencyKeyError",
    "InvalidLabDifficulty",
    "InvalidLearnerExplanationError",
    "InvalidSessionReportEvidenceError",
    "InvalidTransition",
    "LabNotAvailableError",
    "QuotaExceededError",
    "RateLimitedError",
    "RuntimeClientError",
    "SessionEmailPolicyError",
    "SessionExplanationPolicyError",
    "SessionNotFound",
    "SessionNotFoundErrorSessionFeedback",
    "SessionNotFoundErrorSessionHints",
    "SessionNotFoundErrorSessionReportEvidence",
]
