from collections.abc import Callable
from datetime import datetime, timezone
import logging

from apps.control_plane.src.application.session_lifecycle.ports import UnitOfWork
from apps.control_plane.src.domain.session_lifecycle.state_machine import Trigger

from .idempotency import (
    build_expired_provisioning_transition_idempotency_key,
    build_expired_session_transition_idempotency_key,
)
from .policy import ExpiryPolicy
from .ports import ExpirySessionPort
from .types import ExpiryCandidate, ExpiryOnceResult

logger = logging.getLogger(__name__)


class ExpiryHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        policy: ExpiryPolicy,
        transition: Callable[..., object],
        now: datetime,
    ) -> None:
        self._uow = uow
        self._policy = policy
        self._transition = transition
        self._now = now

    def handle(self, session: ExpiryCandidate) -> None:
        created_at = _ensure_utc(session.created_at)
        started_at = (
            _ensure_utc(session.started_at)
            if session.started_at is not None
            else created_at
        )
        if (
            session.state == "PROVISIONING"
            and (self._now - created_at).total_seconds()
            >= self._policy.provisioning_timeout_seconds
        ):
            self._expire(
                session=session,
                trigger=Trigger.PROVISIONING_MAX_TIME,
                reason_code="PROVISIONING_TIMEOUT",
                key=build_expired_provisioning_transition_idempotency_key(
                    session_id=session.session_id,
                    state=session.state,
                ),
            )
            return

        if (
            session.state in {"ACTIVE", "IDLE"}
            and (self._now - started_at).total_seconds()
            >= self._policy.max_session_lifetime_seconds
        ):
            self._expire(
                session=session,
                trigger=Trigger.SESSION_MAX_TIME,
                reason_code="SESSION_MAX_TIME_TIMEOUT",
                key=build_expired_session_transition_idempotency_key(
                    session_id=session.session_id,
                    state=session.state,
                ),
            )

    def _expire(
        self,
        *,
        session: ExpiryCandidate,
        trigger: Trigger,
        reason_code: str,
        key: str,
    ) -> None:
        self._transition(
            session_id=session.session_id,
            trigger=trigger,
            actor="expiry_worker",
            metadata={
                "expiry_reason": reason_code,
                "reason_code": reason_code,
                "state_before": session.state,
            },
            idempotency_key=key,
            uow=self._uow,
        )


def process_expiry_batch(
    *,
    session_query_repo: ExpirySessionPort,
    uow: UnitOfWork,
    policy: ExpiryPolicy,
    transition: Callable[..., object],
    now: datetime | None = None,
) -> ExpiryOnceResult:
    claimed_count = 0
    succeeded_count = 0
    failed_count = 0
    handler = ExpiryHandler(
        uow=uow,
        policy=policy,
        transition=transition,
        now=now or datetime.now(timezone.utc),
    )
    for session in session_query_repo.get_expiry_candidates():
        claimed_count += 1
        try:
            handler.handle(session)
            succeeded_count += 1
        except Exception:
            failed_count += 1
            logger.exception("expiry failed for session_id=%s", session.session_id)

    return ExpiryOnceResult(
        claimed_count=claimed_count,
        succeeded_count=succeeded_count,
        failed_count=failed_count,
        retried_count=0,
    )


def _ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
