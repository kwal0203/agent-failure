from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import logging

from apps.control_plane.src.application.session_lifecycle.ports import UnitOfWork
from apps.control_plane.src.domain.session_lifecycle.state_machine import Trigger

from .idempotency import (
    build_reconcile_failed_runtime_transition_idempotency_key,
    build_reconcile_missing_runtime_transition_idempotency_key,
)
from .ports import ReconciliationSessionQueryPort, RuntimeInspectorPort
from .trace import append_runtime_trace
from .types import (
    ReconciliationCandidate,
    ReconciliationOnceResult,
    RuntimeInspectorRequest,
    RuntimeInspectorResult,
)

logger = logging.getLogger(__name__)

_TERMINAL_STATES = {"COMPLETED", "FAILED", "EXPIRED", "CANCELLED"}


@dataclass
class _ReconciliationCounts:
    claimed: int = 0
    succeeded: int = 0
    failed: int = 0

    def result(self) -> ReconciliationOnceResult:
        return ReconciliationOnceResult(
            claimed_count=self.claimed,
            succeeded_count=self.succeeded,
            failed_count=self.failed,
            retried_count=0,
        )


class ReconciliationHandler:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        inspector: RuntimeInspectorPort,
        transition: Callable[..., object],
    ) -> None:
        self._uow = uow
        self._inspector = inspector
        self._transition = transition

    def handle(self, session: ReconciliationCandidate) -> None:
        if session.state == "ACTIVE" and not _has_runtime_id(session.runtime_id):
            self._transition_runtime_failure(
                session=session,
                reason_code="MISSING_RUNTIME_ID",
                missing_runtime=False,
            )
            return

        inspection = self._inspector.inspect(
            RuntimeInspectorRequest(
                session_id=session.session_id,
                runtime_id=session.runtime_id,
            )
        )
        self._trace_health(session=session, inspection=inspection)

        if session.state in {"PROVISIONING", "ACTIVE"} and not inspection.exists:
            self._transition_runtime_failure(
                session=session,
                reason_code="MISSING_RUNTIME",
                missing_runtime=True,
                inspection=inspection,
            )
            return

        if session.state in _TERMINAL_STATES and inspection.exists:
            self._enqueue_cleanup(
                session=session,
                runtime_id=session.runtime_id,
                reason_code="ORPHAN_RUNTIME_DETECTED",
            )
            return

        if inspection.duplicate_count > 0:
            self._enqueue_duplicate_cleanup(session=session, inspection=inspection)
            return

        if (
            session.state == "ACTIVE"
            and isinstance(inspection.phase, str)
            and inspection.phase.lower() == "failed"
        ):
            self._transition_runtime_failure(
                session=session,
                reason_code="RUNTIME_PHASE_FAILED",
                missing_runtime=False,
                inspection=inspection,
            )

    def _transition_runtime_failure(
        self,
        *,
        session: ReconciliationCandidate,
        reason_code: str,
        missing_runtime: bool,
        inspection: RuntimeInspectorResult | None = None,
    ) -> None:
        trigger = (
            Trigger.PROVISIONING_FAILED
            if session.state == "PROVISIONING"
            else Trigger.RUNTIME_FAILED
        )
        metadata: dict[str, object] = {
            "reconcile_reason": reason_code,
            "reason_code": reason_code,
            "state_before": session.state,
        }
        if inspection is not None:
            metadata.update(
                {
                    "requested_runtime_id": session.runtime_id,
                    "inspector_matched_runtime_ids": list(
                        inspection.matched_runtime_ids
                    ),
                    "inspector_phase": inspection.phase,
                    "inspector_reason": inspection.reason,
                }
            )
        key_builder = (
            build_reconcile_missing_runtime_transition_idempotency_key
            if missing_runtime
            else build_reconcile_failed_runtime_transition_idempotency_key
        )
        self._transition(
            session_id=session.session_id,
            trigger=trigger,
            actor="reconciliation_worker",
            metadata=metadata,
            idempotency_key=key_builder(
                session_id=session.session_id,
                state=session.state,
            ),
            uow=self._uow,
        )

    def _enqueue_duplicate_cleanup(
        self,
        *,
        session: ReconciliationCandidate,
        inspection: RuntimeInspectorResult,
    ) -> None:
        matched = tuple(sorted(set(inspection.matched_runtime_ids)))
        keeper = session.runtime_id if session.runtime_id in matched else matched[0]
        logger.critical(
            "duplicate runtimes detected session_id=%s keeper=%s matched=%s",
            session.session_id,
            keeper,
            matched,
        )
        for runtime_id in matched:
            if runtime_id != keeper:
                self._enqueue_cleanup(
                    session=session,
                    runtime_id=runtime_id,
                    reason_code="DUPLICATE_RUNTIME_DETECTED",
                )

    def _enqueue_cleanup(
        self,
        *,
        session: ReconciliationCandidate,
        runtime_id: str | None,
        reason_code: str,
    ) -> None:
        with self._uow.transaction():
            self._uow.outbox.enqueue_for_cleanup(
                session_id=session.session_id,
                runtime_id=runtime_id,
                terminal_state=session.state,
                reason_code=reason_code,
                requested_at=datetime.now(timezone.utc),
            )

    def _trace_health(
        self,
        *,
        session: ReconciliationCandidate,
        inspection: RuntimeInspectorResult,
    ) -> None:
        append_runtime_trace(
            uow=self._uow,
            session_id=session.session_id,
            event_type="RUNTIME_HEALTH_STATUS",
            source="control-plane-reconciliation-worker",
            payload={
                "exists": inspection.exists,
                "phase": inspection.phase,
                "reason": inspection.reason,
                "duplicate_count": inspection.duplicate_count,
                "matched_runtime_ids_count": len(inspection.matched_runtime_ids),
                "requested_runtime_id": inspection.requested_runtime_id,
            },
        )


def _has_runtime_id(runtime_id: str | None) -> bool:
    return runtime_id is not None and bool(runtime_id.strip())


def process_reconciliation_batch(
    *,
    session_query_repo: ReconciliationSessionQueryPort,
    uow: UnitOfWork,
    inspector: RuntimeInspectorPort,
    transition: Callable[..., object],
) -> ReconciliationOnceResult:
    counts = _ReconciliationCounts()
    handler = ReconciliationHandler(
        uow=uow,
        inspector=inspector,
        transition=transition,
    )
    for session in session_query_repo.get_reconciliation_candidates():
        counts.claimed += 1
        try:
            handler.handle(session)
            counts.succeeded += 1
        except Exception:
            counts.failed += 1
            logger.exception(
                "reconciliation failed for session_id=%s",
                session.session_id,
            )
    return counts.result()
