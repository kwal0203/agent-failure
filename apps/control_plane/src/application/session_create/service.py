from uuid import UUID
from .types import PrincipalContext
from .ports import AdmissionPolicy, CreateSessionUnitOfWork
from .errors import (
    LabNotAvailableError,
    QuotaExceededError,
    DegradedModeRestrictionError,
    InvalidIdempotencyKeyError,
    ForbiddenError,
    RateLimitedError,
    AdmissionDecisionError,
    DuplicateIdempotencyKeyError,
)
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
    lab_id: UUID,
    idempotency_key: str,
    uow: CreateSessionUnitOfWork,
) -> CreateSessionResult:
    try:
        with uow.transaction():
            # - authenticated learner or admin acting as a learner
            if principal.role not in {"learner", "admin"}:
                raise ForbiddenError(role=principal.role)

            # - validates lab availability
            if not uow.lab_repo.validate_lab(lab_id=lab_id):
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
                        message=decision.message or "You are in degraded mode.",
                        details=details,
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
            existing = uow.idempotency.get(
                operation="create_session", key=idempotency_key
            )
            if existing is not None:
                if (
                    lab_id != existing.lab_id
                    or existing.requester_user_id != principal.user_id
                ):
                    raise InvalidIdempotencyKeyError(idem_key=str(idempotency_key))
                return existing

            # - creates a durable session row if the idempotency key has not been used
            session = uow.sessions.create_provision_session(
                lab_id=lab_id, actor_id=principal.user_id, actor_role=principal.role
            )
            uow.idempotency.save(
                operation="create_session", key=idempotency_key, result=session
            )

            # TODO: Outbox enqueue
            # NOTE: Are the session attributes immediately available after session creation?
            uow.outbox.enqueue_for_session_creation(
                session_id=session.session_id,
                lab_id=lab_id,
                lab_version_id=session.lab_version_id,
                resume_mode=session.resume_mode,
                requester_user_id=principal.user_id,
                idempotency_key=idempotency_key,
                requested_at=session.created_at,
            )

            return session
    except DuplicateIdempotencyKeyError:
        with uow.transaction():
            # reload by key
            existing = uow.idempotency.get(
                operation="create_session", key=idempotency_key
            )
            if existing is not None:
                if (
                    lab_id != existing.lab_id
                    or existing.requester_user_id != principal.user_id
                ):
                    raise InvalidIdempotencyKeyError(idem_key=str(idempotency_key))
                return existing

            raise RuntimeError("Idempotency conflict but no existing record found.")
