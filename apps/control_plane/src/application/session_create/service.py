from uuid import UUID
from .types import PrincipalContext
from .ports import LabRepository, AdmissionPolicy, CreateSessionRepository
from .errors import (
    LabNotAvailableError,
    QuotaExceededError,
    DegradedModeRestrictionError,
    InvalidIdempotencyKeyError,
    ForbiddenError,
    RateLimitedError,
    AdmissionDecisionError,
)
from apps.control_plane.src.application.common.ports import IdempotencyStore
from .schemas import CreateSessionResult


def _to_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default

    return default


def create_session(
    principal: PrincipalContext,
    admission_policy: AdmissionPolicy,
    lab_repo: LabRepository,
    sessions: CreateSessionRepository,
    idempotency_store: IdempotencyStore[CreateSessionResult],
    lab_id: UUID,
    idempotency_key: str,
) -> CreateSessionResult:
    # - authenticated learner or admin acting as a learner
    if principal.role not in {"learner", "admin"}:
        raise ForbiddenError(role=principal.role)

    # - validates lab availability
    if not lab_repo.validate_lab(lab_id=lab_id):
        raise LabNotAvailableError(lab_id=lab_id)

    # - validates quota restrictions
    decision = admission_policy.check_launch_allowed(
        user_id=principal.user_id, lab_id=lab_id
    )
    if not decision.allowed:
        details = decision.details or {}

        if decision.code == "QUOTA_EXCEEDED":
            current = _to_int(details.get("current"))
            quota = _to_int(details.get("quota"))
            raise QuotaExceededError(
                current=current,
                quota=quota,
                message=decision.message or "You have exceeded your quota.",
                details=details,
            )
        elif decision.code == "DEGRADED_MODE_RESTRICTION":
            raise DegradedModeRestrictionError(
                message=decision.message or "You are in degraded mode.", details=details
            )
        elif decision.code == "RATE_LIMITED":
            limit = _to_int(details.get("limit"))
            raise RateLimitedError(
                limit=limit,
                message=decision.message or "You have been rate limited.",
                details=details,
            )

        raise AdmissionDecisionError(code=decision.code, details=details)

    # - validate idempotency
    existing = idempotency_store.get(operation="create_session", key=idempotency_key)
    if existing is not None:
        if lab_id != existing.lab_id or existing.requester_user_id != principal.user_id:
            raise InvalidIdempotencyKeyError(idem_key=str(idempotency_key))
        return existing

    # - creates a durable session row if the idempotency key has not been used
    session = sessions.create_provision_session(
        lab_id=lab_id, actor_id=principal.user_id, actor_role=principal.role
    )
    idempotency_store.save(
        operation="create_session", key=idempotency_key, result=session
    )
    return session
