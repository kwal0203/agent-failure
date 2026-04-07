from uuid import UUID
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.common.errors import ForbiddenError

from .ports import AdmissionPolicy, CreateSessionUnitOfWork
from .errors import (
    LabNotAvailableError,
    QuotaExceededError,
    DegradedModeRestrictionError,
    InvalidIdempotencyKeyError,
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


def _return_existing_session(
    uow: CreateSessionUnitOfWork,
    principal: PrincipalContext,
    lab_id: UUID,
    idempotency_key: str,
) -> CreateSessionResult | None:
    existing = uow.idempotency.get(operation="create_session", key=idempotency_key)
    if existing is not None:
        if lab_id != existing.lab_id or existing.requester_user_id != principal.user_id:
            raise InvalidIdempotencyKeyError(idem_key=str(idempotency_key))
        return existing

    return None


def create_session(
    principal: PrincipalContext,
    admission_policy: AdmissionPolicy,
    lab_id: UUID,
    idempotency_key: str,
    uow: CreateSessionUnitOfWork,
    lab_difficulty: str = "medium",
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

            # Check if session already exists
            existing = _return_existing_session(
                uow=uow,
                principal=principal,
                lab_id=lab_id,
                idempotency_key=idempotency_key,
            )
            if existing:
                return existing

            # Add new session now that session has been confirmed to be 'not existing'
            session = uow.sessions.create_provision_session(
                lab_id=lab_id,
                lab_difficulty=lab_difficulty,
                actor_id=principal.user_id,
                actor_role=principal.role,
            )
            uow.idempotency.save(
                operation="create_session", key=idempotency_key, result=session
            )

            lab_version_id = session.lab_version_id
            if lab_version_id is None:
                raise RuntimeError(
                    "create_session produced session without a lab_version_id"
                )

            binding = uow.lab_repo.get_runtime_binding(
                lab_id=session.lab_id, lab_version_id=lab_version_id
            )
            uow.outbox.enqueue_for_session_creation(
                session_id=session.session_id,
                lab_id=lab_id,
                lab_version_id=lab_version_id,
                lab_slug=binding.lab_slug,
                lab_version=binding.lab_version,
                resume_mode=session.resume_mode,
                requester_user_id=principal.user_id,
                idempotency_key=idempotency_key,
                requested_at=session.created_at,
            )

            return session

    except DuplicateIdempotencyKeyError:
        with uow.transaction():
            # Concurrent create-session requests can both observe "no record" and race
            # to insert the same idempotency key. The loser gets a unique-constraint
            # failure (mapped to DuplicateIdempotencyKeyError), so we must reload and
            # re-validate request identity (lab + requester) before returning the
            # existing result.
            existing = _return_existing_session(
                uow=uow,
                principal=principal,
                lab_id=lab_id,
                idempotency_key=idempotency_key,
            )
            if existing:
                return existing

            raise RuntimeError("Idempotency conflict but no existing record found.")
