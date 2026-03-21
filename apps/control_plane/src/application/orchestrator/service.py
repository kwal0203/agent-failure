from apps.control_plane.src.domain.session_lifecycle.state_machine import Trigger
from apps.control_plane.src.application.session_lifecycle.service import (
    transition_session,
)
from apps.control_plane.src.application.session_lifecycle.errors import (
    SessionNotFound,
    InvalidTransition,
    TransitionValidationError,
)
from apps.control_plane.src.application.session_lifecycle.ports import UnitOfWork
from apps.control_plane.src.infrastructure.runtime.errors import (
    ImageNotFoundError,
    ImageRevokedError,
    InvalidImageLockError,
    DefaultSelectionError,
)
from apps.control_plane.src.infrastructure.persistence.errors import (
    DataIntegrityError,
    StateMismatch,
)
from .ports import (
    ProcessPendingOnceUnitOfWork,
    ProcessCleanupOnceUnitOfWork,
    RuntimeProvisionerPort,
    RuntimeImageResolverPort,
    RuntimeInspectorPort,
    RuntimeTeardownPort,
    ReconciliationSessionQueryPort,
    ExpirySessionPort,
)
from .types import (
    RuntimeProvisionRequest,
    ProcessPendingOnceResult,
    ProcessCleanupOnceResult,
    RuntimeTeardownRequest,
    RuntimeInspectorRequest,
    ReconciliationOnceResult,
    ExpiryOnceResult,
)

from uuid import UUID
from datetime import datetime, timezone

import logging

logger = logging.getLogger(__name__)


# TODO: these hardcoded constants should move to config/env later
MAX_CLEANUP_ATTEMPTS = 3
CLEANUP_BACKOFF_SECONDS = 15

PROVISIONING_TIMEOUT_SECONDS = 900
MAX_SESSION_LIFETIME_SECONDS = 86_400
IDLE_TIMEOUT_SECONDS = 3_600


def _invalid_outbox_payload(
    uow: ProcessPendingOnceUnitOfWork,
    outbox_event_id: UUID,
    error_message: str = "INVALID_OUTBOX_PAYLOAD",
):
    uow.outbox.mark_terminal_failure(
        outbox_event_id=outbox_event_id,
        error_message=error_message,
        failed_at=datetime.now(timezone.utc),
    )


def _ensure_utc(dt: datetime) -> datetime:
    return (
        dt.replace(tzinfo=timezone.utc)
        if dt.tzinfo is None
        else dt.astimezone(timezone.utc)
    )


def process_pending_once(
    uow: ProcessPendingOnceUnitOfWork,
    image_resolver: RuntimeImageResolverPort,
    provisioner: RuntimeProvisionerPort,
) -> ProcessPendingOnceResult:

    claimed_count = 0
    succeeded_count = 0
    failed_count = 0
    retried_count = 0  # Not yet implemented

    try:
        with uow.transaction():
            events = uow.outbox.claim_pending_provisioning()
            for event in events:
                claimed_count += 1

                outbox_event_id = event.outbox_event_id
                session_id = event.session_id
                lab_id_raw = event.payload.get("lab_id")
                lab_version_id_raw = event.payload.get("lab_version_id")
                attempt_count = event.attempt_count

                if not (
                    isinstance(lab_id_raw, str) and isinstance(lab_version_id_raw, str)
                ):
                    _invalid_outbox_payload(uow, outbox_event_id)
                    failed_count += 1
                    continue

                try:
                    lab_id = UUID(lab_id_raw)
                    lab_version_id = UUID(lab_version_id_raw)
                except ValueError:
                    _invalid_outbox_payload(uow, outbox_event_id)
                    failed_count += 1
                    continue

                try:
                    binding = uow.lab.get_runtime_binding(
                        lab_id=lab_id, lab_version_id=lab_version_id
                    )
                    image_ref = image_resolver.resolve(
                        lab_slug=binding.lab_slug, lab_version=binding.lab_version
                    )
                    runtime_request = RuntimeProvisionRequest(
                        session_id=session_id,
                        lab_id=lab_id,
                        lab_version_id=lab_version_id,
                        image_ref=image_ref,
                        metadata={
                            "outbox_event_id": str(outbox_event_id),
                            "attempt_count": attempt_count,
                            "requested_by": "control-plane-outbox-worker",
                            "idempotency_key": f"provision:{event.session_id}:{outbox_event_id}",
                        },
                    )

                    provision_result = provisioner.provision(runtime_request)
                    if (
                        provision_result.status == "accepted"
                        or provision_result.status == "ready"
                    ):
                        uow.outbox.mark_processed(
                            outbox_event_id=event.outbox_event_id,
                            processed_at=datetime.now(timezone.utc),
                        )
                        transition_session(
                            session_id=session_id,
                            trigger=Trigger.PROVISIONING_SUCCEEDED,
                            actor="orchestrator_worker",
                            metadata={"outbox_event_id": str(outbox_event_id)},
                            idempotency_key=f"provisioning:{session_id}:{outbox_event_id}:succeeded",
                            uow=uow.lifecycle_uow,
                        )
                        succeeded_count += 1
                    elif provision_result.status == "failed":
                        uow.outbox.mark_terminal_failure(
                            outbox_event_id=event.outbox_event_id,
                            error_message="Provisioning failed",
                            failed_at=datetime.now(timezone.utc),
                        )
                        transition_session(
                            session_id=session_id,
                            trigger=Trigger.PROVISIONING_FAILED,
                            actor="orchestrator_worker",
                            metadata={
                                "outbox_event_id": str(event.outbox_event_id),
                                "reason_code": provision_result.reason_code
                                or "PROVISIONING_FAILED",
                            },
                            idempotency_key=f"provisioning:{session_id}:{outbox_event_id}:failed",
                            uow=uow.lifecycle_uow,
                        )
                        failed_count += 1
                except (
                    ImageNotFoundError,
                    ImageRevokedError,
                    InvalidImageLockError,
                    DefaultSelectionError,
                    SessionNotFound,
                    InvalidTransition,
                    TransitionValidationError,
                    DataIntegrityError,
                    StateMismatch,
                    ValueError,
                    TypeError,
                ):
                    _invalid_outbox_payload(uow, outbox_event_id)
                    failed_count += 1
                    continue

    except Exception:
        logger.exception("process_pending_once batch failed")

    return ProcessPendingOnceResult(
        claimed_count=claimed_count,
        succeeded_count=succeeded_count,
        failed_count=failed_count,
        retried_count=retried_count,
    )


def process_cleanup_pending_once(
    uow: ProcessCleanupOnceUnitOfWork, teardown: RuntimeTeardownPort
) -> ProcessCleanupOnceResult:

    claimed_count = 0
    succeeded_count = 0
    failed_count = 0
    retried_count = 0

    try:
        with uow.transaction():
            events = uow.outbox.claim_pending_cleanup()
            for event in events:
                ts = datetime.now(timezone.utc)

                claimed_count += 1

                outbox_event_id = event.outbox_event_id
                session_id = event.session_id
                runtime_id = event.payload.get("runtime_id")
                terminal_state = event.payload.get("terminal_state")
                reason_code = event.payload.get("reason_code")
                attempt_count = event.attempt_count

                if not (isinstance(runtime_id, str) or runtime_id is None):
                    uow.outbox.mark_terminal_failure(
                        outbox_event_id=outbox_event_id,
                        error_message="INVALID_CLEANUP_PAYLOAD_RUNTIME_ID",
                        failed_at=ts,
                    )
                    failed_count += 1
                    continue
                if not (isinstance(reason_code, str) or reason_code is None):
                    uow.outbox.mark_terminal_failure(
                        outbox_event_id=outbox_event_id,
                        error_message="INVALID_CLEANUP_PAYLOAD_REASON_CODE",
                        failed_at=ts,
                    )
                    failed_count += 1
                    continue
                if not (isinstance(terminal_state, str) or terminal_state is None):
                    uow.outbox.mark_terminal_failure(
                        outbox_event_id=outbox_event_id,
                        error_message="INVALID_CLEANUP_PAYLOAD_TERMINAL_STATE",
                        failed_at=ts,
                    )
                    failed_count += 1
                    continue
                if terminal_state is not None and terminal_state not in {
                    "COMPLETED",
                    "FAILED",
                    "EXPIRED",
                    "CANCELLED",
                }:
                    uow.outbox.mark_terminal_failure(
                        outbox_event_id=outbox_event_id,
                        error_message="INVALID_CLEANUP_PAYLOAD_TERMINAL_STATE",
                        failed_at=ts,
                    )
                    failed_count += 1
                    continue

                teardown_request = RuntimeTeardownRequest(
                    session_id=session_id,
                    runtime_id=runtime_id,
                    metadata={
                        "outbox_event_id": str(outbox_event_id),
                        "terminal_state": terminal_state,
                        "reason_code": reason_code,
                        "attempt_count": attempt_count,
                    },
                )

                try:
                    teardown_result = teardown.teardown(teardown_request)
                    if teardown_result.status in {"already_gone", "deleted"}:
                        uow.outbox.mark_processed(
                            outbox_event_id=outbox_event_id, processed_at=ts
                        )
                        succeeded_count += 1
                    elif teardown_result.status == "failed":
                        reason = teardown_result.reason_code or "TEARDOWN_FAILED"
                        retryable_reasons = {
                            "K8S_API_UNAVAILABLE",
                            "K8S_TIMEOUT",
                            "ORCHESTRATOR_UNAVAILABLE",
                        }

                        if (
                            reason in retryable_reasons
                            and attempt_count < MAX_CLEANUP_ATTEMPTS
                        ):
                            uow.outbox.mark_retryable_failure(
                                outbox_event_id=outbox_event_id,
                                error_message=reason,
                                backoff_seconds=CLEANUP_BACKOFF_SECONDS,
                                failed_at=ts,
                            )
                            retried_count += 1
                        else:
                            uow.outbox.mark_terminal_failure(
                                outbox_event_id=outbox_event_id,
                                error_message=reason,
                                failed_at=ts,
                            )
                            failed_count += 1
                except Exception:
                    reason = "CLEANUP_TEARDOWN_EXCEPTION"
                    if attempt_count < MAX_CLEANUP_ATTEMPTS:
                        uow.outbox.mark_retryable_failure(
                            outbox_event_id=outbox_event_id,
                            error_message=reason,
                            backoff_seconds=CLEANUP_BACKOFF_SECONDS,
                            failed_at=ts,
                        )
                        retried_count += 1
                    else:
                        uow.outbox.mark_terminal_failure(
                            outbox_event_id=outbox_event_id,
                            error_message="CLEANUP_TEARDOWN_EXCEPTION",
                            failed_at=ts,
                        )
                        failed_count += 1
                    continue

    except Exception:
        logger.exception("process_cleanup_pending_once batch failed")

    return ProcessCleanupOnceResult(
        claimed_count=claimed_count,
        succeeded_count=succeeded_count,
        failed_count=failed_count,
        retried_count=retried_count,
    )


def process_reconciliation_once(
    session_query_repo: ReconciliationSessionQueryPort,
    uow: UnitOfWork,
    inspector: RuntimeInspectorPort,
) -> ReconciliationOnceResult:

    claimed_count = 0
    succeeded_count = 0
    failed_count = 0
    # retried_count = 0

    sessions = session_query_repo.get_reconciliation_candidates()
    for session in sessions:
        session_id = session.session_id
        try:
            ts = datetime.now(timezone.utc)

            claimed_count += 1

            state = session.state
            runtime_id = session.runtime_id
            # runtime_substate = session.runtime_substate

            inspection_request = RuntimeInspectorRequest(
                session_id=session_id, runtime_id=runtime_id
            )
            inspection_result = inspector.inspect(inspection_request)
            if state in {"PROVISIONING", "ACTIVE"} and not inspection_result.exists:
                trigger = (
                    Trigger.PROVISIONING_FAILED
                    if state == "PROVISIONING"
                    else Trigger.RUNTIME_FAILED
                )
                transition_session(
                    session_id=session_id,
                    trigger=trigger,
                    actor="reconciliation_worker",
                    metadata={
                        "reconcile_reason": "MISSING_RUNTIME",
                        "reason_code": "MISSING_RUNTIME",
                        "state_before": state,
                        "requested_runtime_id": runtime_id,
                        "inspector_matched_runtime_ids": list(
                            inspection_result.matched_runtime_ids
                        ),
                        "inspector_phase": inspection_result.phase,
                        "inspector_reason": inspection_result.reason,
                    },
                    idempotency_key=f"reconcile:{session_id}:missing-runtime:{state}",
                    uow=uow,
                )
                succeeded_count += 1
                continue

            if (
                state in {"COMPLETED", "FAILED", "EXPIRED", "CANCELLED"}
                and inspection_result.exists
            ):
                with uow.transaction():
                    uow.outbox.enqueue_for_cleanup(
                        session_id=session_id,
                        runtime_id=runtime_id,
                        terminal_state=state,
                        reason_code="ORPHAN_RUNTIME_DETECTED",
                        requested_at=ts,
                    )
                succeeded_count += 1
                continue

            if inspection_result.duplicate_count > 0:
                # duplicate runtimes, emit critical log + enqueue cleanup job for n-1 duplicates
                logger.critical(
                    "duplicate runtimes detected session_id=%s matched=%s",
                    session_id,
                    inspection_result.matched_runtime_ids,
                )

                with uow.transaction():
                    # TODO(E1-T5 follow-up): when session.runtime_id is None, this branch
                    # will enqueue cleanup for all matched runtimes. Add a deterministic
                    # keeper-selection policy once runtime identity guarantees are tighter.
                    for duplicate in inspection_result.matched_runtime_ids:
                        if duplicate == runtime_id:
                            continue
                        uow.outbox.enqueue_for_cleanup(
                            session_id=session_id,
                            runtime_id=duplicate,
                            terminal_state=state,
                            reason_code="DUPLICATE_RUNTIME_DETECTED",
                            requested_at=ts,
                        )
                succeeded_count += 1
                continue

            if (
                state == "ACTIVE"
                and isinstance(inspection_result.phase, str)
                and inspection_result.phase.lower() == "failed"
            ):
                # runtime crashed, transition session state to failed
                transition_session(
                    session_id=session_id,
                    trigger=Trigger.RUNTIME_FAILED,
                    actor="reconciliation_worker",
                    metadata={
                        "reconcile_reason": "RUNTIME_PHASE_FAILED",
                        "reason_code": "RUNTIME_PHASE_FAILED",
                        "state_before": state,
                        "requested_runtime_id": runtime_id,
                        "inspector_matched_runtime_ids": list(
                            inspection_result.matched_runtime_ids
                        ),
                        "inspector_phase": inspection_result.phase,
                        "inspector_reason": inspection_result.reason,
                    },
                    idempotency_key=f"reconcile:{session_id}:failed-runtime:{state}",
                    uow=uow,
                )
                succeeded_count += 1
                continue

            succeeded_count += 1

        except Exception:
            failed_count += 1
            logger.exception("reconciliation failed for session_id=%s", session_id)
            continue

    return ReconciliationOnceResult(
        claimed_count=claimed_count,
        succeeded_count=succeeded_count,
        failed_count=failed_count,
        retried_count=0,
    )


def process_expiry_once(
    session_query_repo: ExpirySessionPort, uow: UnitOfWork
) -> ExpiryOnceResult:

    claimed_count = 0
    succeeded_count = 0
    failed_count = 0
    # retried_count = 0

    sessions = session_query_repo.get_expiry_candidates()
    ts = datetime.now(timezone.utc)
    for session in sessions:
        claimed_count += 1

        session_id = session.session_id
        state = session.state

        created_at = _ensure_utc(session.created_at)
        started_at = (
            _ensure_utc(session.started_at) if session.started_at else created_at
        )

        try:
            if (
                session.state == "PROVISIONING"
                and (ts - created_at).total_seconds() >= PROVISIONING_TIMEOUT_SECONDS
            ):
                transition_session(
                    session_id=session_id,
                    trigger=Trigger.PROVISIONING_MAX_TIME,
                    actor="expiry_worker",
                    metadata={
                        "expiry_reason": "PROVISIONING_TIMEOUT",
                        "reason_code": "PROVISIONING_TIMEOUT",
                        "state_before": state,
                    },
                    idempotency_key=f"expiry:{session_id}:expired-provisioning:{state}",
                    uow=uow,
                )
                succeeded_count += 1
                continue

            if (
                session.state in {"ACTIVE", "IDLE"}
                and (ts - started_at).total_seconds() >= MAX_SESSION_LIFETIME_SECONDS
            ):
                transition_session(
                    session_id=session_id,
                    trigger=Trigger.SESSION_MAX_TIME,
                    actor="expiry_worker",
                    metadata={
                        "expiry_reason": "SESSION_MAX_TIME_TIMEOUT",
                        "reason_code": "SESSION_MAX_TIME_TIMEOUT",
                        "state_before": state,
                    },
                    idempotency_key=f"expiry:{session_id}:expired-session:{state}",
                    uow=uow,
                )
                succeeded_count += 1
                continue

            succeeded_count += 1

            # TODO(P0-E1 follow-up): idle-time expiry is intentionally deferred.
            # Accurate IDLE timeout needs a persisted `last_activity_at` source of truth,
            # which requires schema + write-path changes and is out of scope for T6.

        except Exception:
            failed_count += 1
            logger.exception("expiry failed for session_id=%s", session_id)
            continue

    return ExpiryOnceResult(
        claimed_count=claimed_count,
        succeeded_count=succeeded_count,
        failed_count=failed_count,
        retried_count=0,
    )
