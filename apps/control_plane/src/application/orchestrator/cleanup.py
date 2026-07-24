from dataclasses import dataclass
from datetime import datetime, timezone
import logging

from .policy import CleanupPolicy
from .ports import ProcessCleanupOnceUnitOfWork, RuntimeTeardownPort
from .types import (
    PendingCleanupEvent,
    ProcessCleanupOnceResult,
    RuntimeTeardownRequest,
)

logger = logging.getLogger(__name__)

_TERMINAL_STATES = {"COMPLETED", "FAILED", "EXPIRED", "CANCELLED"}
_RETRYABLE_FAILURE_REASONS = {
    "K8S_API_UNAVAILABLE",
    "K8S_RESOURCES_STILL_EXIST",
    "K8S_TIMEOUT",
    "ORCHESTRATOR_UNAVAILABLE",
}


@dataclass
class _CleanupCounts:
    claimed: int = 0
    succeeded: int = 0
    failed: int = 0
    retried: int = 0

    def result(self) -> ProcessCleanupOnceResult:
        return ProcessCleanupOnceResult(
            claimed_count=self.claimed,
            succeeded_count=self.succeeded,
            failed_count=self.failed,
            retried_count=self.retried,
        )


class CleanupEventHandler:
    def __init__(
        self,
        *,
        uow: ProcessCleanupOnceUnitOfWork,
        teardown: RuntimeTeardownPort,
        policy: CleanupPolicy,
    ) -> None:
        self._uow = uow
        self._teardown = teardown
        self._policy = policy

    def handle(self, event: PendingCleanupEvent, counts: _CleanupCounts) -> None:
        timestamp = datetime.now(timezone.utc)
        payload = self._validated_payload(event=event, timestamp=timestamp)
        if payload is None:
            counts.failed += 1
            return

        runtime_id, terminal_state, reason_code = payload
        request = RuntimeTeardownRequest(
            session_id=event.session_id,
            runtime_id=runtime_id,
            metadata={
                "outbox_event_id": str(event.outbox_event_id),
                "terminal_state": terminal_state,
                "reason_code": reason_code,
                "attempt_count": event.attempt_count,
            },
        )
        pod_name = runtime_id or f"session-{str(event.session_id)[:8]}"

        try:
            result = self._teardown.teardown(request)
        except Exception:
            logger.exception(
                "cleanup teardown exception session_id=%s outbox_event_id=%s "
                "pod_name=%s attempt_count=%s",
                event.session_id,
                event.outbox_event_id,
                pod_name,
                event.attempt_count,
            )
            self._retry_or_fail(
                event=event,
                reason="CLEANUP_TEARDOWN_EXCEPTION",
                timestamp=timestamp,
                counts=counts,
            )
            return

        logger.info(
            "cleanup teardown result session_id=%s outbox_event_id=%s pod_name=%s "
            "status=%s reason_code=%s details=%s",
            event.session_id,
            event.outbox_event_id,
            pod_name,
            result.status,
            result.reason_code,
            result.details,
        )
        if result.status in {"already_gone", "deleted"}:
            self._handle_delete_acknowledged(
                event=event,
                teardown_status=result.status,
                terminal_state=terminal_state,
                timestamp=timestamp,
                pod_name=pod_name,
                counts=counts,
            )
            return

        reason = result.reason_code or "TEARDOWN_FAILED"
        self._retry_or_fail(
            event=event,
            reason=reason,
            timestamp=timestamp,
            counts=counts,
            retryable=reason in _RETRYABLE_FAILURE_REASONS,
        )
        logger.warning(
            "cleanup teardown failed session_id=%s outbox_event_id=%s pod_name=%s "
            "attempt_count=%s reason=%s retryable=%s",
            event.session_id,
            event.outbox_event_id,
            pod_name,
            event.attempt_count,
            reason,
            reason in _RETRYABLE_FAILURE_REASONS,
        )

    def _validated_payload(
        self, *, event: PendingCleanupEvent, timestamp: datetime
    ) -> tuple[str | None, str | None, str | None] | None:
        runtime_id = event.payload.get("runtime_id")
        reason_code = event.payload.get("reason_code")
        terminal_state = event.payload.get("terminal_state")
        fields = (
            ("RUNTIME_ID", runtime_id),
            ("REASON_CODE", reason_code),
            ("TERMINAL_STATE", terminal_state),
        )
        for field_name, value in fields:
            if not (isinstance(value, str) or value is None):
                self._mark_terminal(
                    event=event,
                    reason=f"INVALID_CLEANUP_PAYLOAD_{field_name}",
                    timestamp=timestamp,
                )
                return None
        if terminal_state is not None and terminal_state not in _TERMINAL_STATES:
            self._mark_terminal(
                event=event,
                reason="INVALID_CLEANUP_PAYLOAD_TERMINAL_STATE",
                timestamp=timestamp,
            )
            return None
        return runtime_id, terminal_state, reason_code

    def _handle_delete_acknowledged(
        self,
        *,
        event: PendingCleanupEvent,
        teardown_status: str,
        terminal_state: str | None,
        timestamp: datetime,
        pod_name: str,
        counts: _CleanupCounts,
    ) -> None:
        if (
            teardown_status == "already_gone"
            and terminal_state in _TERMINAL_STATES
            and event.attempt_count == 0
        ):
            # Reverify once to absorb a late-create race after a not-found response.
            self._uow.outbox.mark_retryable_failure(
                outbox_event_id=event.outbox_event_id,
                error_message="CLEANUP_ALREADY_GONE_REVERIFY",
                backoff_seconds=self._policy.already_gone_reverify_backoff_seconds,
                failed_at=timestamp,
            )
            counts.retried += 1
            return

        try:
            resources_still_exist = self._teardown.resources_exist(
                str(event.session_id)
            )
        except Exception:
            resources_still_exist = True

        if resources_still_exist:
            self._retry_or_fail(
                event=event,
                reason="CLEANUP_RESOURCES_STILL_EXIST",
                timestamp=timestamp,
                counts=counts,
            )
            logger.warning(
                "cleanup verification failed session_id=%s outbox_event_id=%s "
                "pod_name=%s attempt_count=%s reason=%s",
                event.session_id,
                event.outbox_event_id,
                pod_name,
                event.attempt_count,
                "CLEANUP_RESOURCES_STILL_EXIST",
            )
            return

        self._uow.outbox.mark_processed(
            outbox_event_id=event.outbox_event_id,
            processed_at=timestamp,
        )
        counts.succeeded += 1

    def _retry_or_fail(
        self,
        *,
        event: PendingCleanupEvent,
        reason: str,
        timestamp: datetime,
        counts: _CleanupCounts,
        retryable: bool = True,
    ) -> None:
        if retryable and event.attempt_count < self._policy.max_attempts:
            self._uow.outbox.mark_retryable_failure(
                outbox_event_id=event.outbox_event_id,
                error_message=reason,
                backoff_seconds=self._policy.retry_backoff_seconds,
                failed_at=timestamp,
            )
            counts.retried += 1
            return
        self._mark_terminal(event=event, reason=reason, timestamp=timestamp)
        counts.failed += 1

    def _mark_terminal(
        self, *, event: PendingCleanupEvent, reason: str, timestamp: datetime
    ) -> None:
        self._uow.outbox.mark_terminal_failure(
            outbox_event_id=event.outbox_event_id,
            error_message=reason,
            failed_at=timestamp,
        )


def process_cleanup_batch(
    *,
    uow: ProcessCleanupOnceUnitOfWork,
    teardown: RuntimeTeardownPort,
    policy: CleanupPolicy,
) -> ProcessCleanupOnceResult:
    counts = _CleanupCounts()
    handler = CleanupEventHandler(uow=uow, teardown=teardown, policy=policy)
    try:
        with uow.transaction():
            for event in uow.outbox.claim_pending_cleanup():
                counts.claimed += 1
                handler.handle(event, counts)
    except Exception:
        logger.exception("process_cleanup_pending_once batch failed")
    return counts.result()
