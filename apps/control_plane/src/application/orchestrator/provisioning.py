from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
import time
from typing import Literal
from uuid import UUID

from pydantic import ValidationError

from apps.control_plane.src.application.session_hints.service import (
    initialize_session_hints,
)
from apps.control_plane.src.application.session_objectives.service import (
    initialize_session_objectives,
)
from apps.control_plane.src.domain.session_lifecycle.state_machine import (
    SessionState,
    Trigger,
)
from apps.control_plane.src.infrastructure.persistence.errors import (
    DataIntegrityError,
    StateMismatch,
)
from apps.control_plane.src.infrastructure.runtime.errors import (
    DefaultSelectionError,
    ImageNotFoundError,
    ImageRevokedError,
    InvalidImageLockError,
)
from apps.control_plane.src.application.session_lifecycle.errors import (
    InvalidTransition,
    SessionNotFound,
    TransitionValidationError,
)
from apps.control_plane.src.application.session_lifecycle.ports import SessionRow

from .idempotency import (
    build_provision_request_idempotency_key,
    build_provisioning_failed_transition_idempotency_key,
    build_provisioning_succeeded_transition_idempotency_key,
)
from .policy import ProvisioningPolicy
from .ports import (
    ProcessPendingOnceUnitOfWork,
    RuntimeImageResolverPort,
    RuntimeInspectorPort,
    RuntimeProvisionerPort,
)
from .schemas import ProvisioningPayload
from .trace import append_runtime_trace
from .types import (
    PendingProvisioningEvent,
    ProcessPendingOnceResult,
    ProvisionResult,
    RuntimeInspectorRequest,
    RuntimeInspectorResult,
    RuntimeProvisionRequest,
    UpsertSessionRuntimeBindingInput,
)

logger = logging.getLogger(__name__)

_TERMINAL_SESSION_STATES = {
    SessionState.CANCELLED,
    SessionState.COMPLETED,
    SessionState.FAILED,
    SessionState.EXPIRED,
}
_EXPECTED_EVENT_ERRORS = (
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
)
_EventOutcome = Literal["succeeded", "failed", "retried"]


@dataclass
class _ProvisioningCounts:
    claimed: int = 0
    succeeded: int = 0
    failed: int = 0
    retried: int = 0

    def record(self, outcome: _EventOutcome) -> None:
        if outcome == "succeeded":
            self.succeeded += 1
        elif outcome == "failed":
            self.failed += 1
        else:
            self.retried += 1

    def result(self) -> ProcessPendingOnceResult:
        return ProcessPendingOnceResult(
            claimed_count=self.claimed,
            succeeded_count=self.succeeded,
            failed_count=self.failed,
            retried_count=self.retried,
        )


@dataclass(frozen=True)
class _ProvisioningContext:
    event: PendingProvisioningEvent
    payload: ProvisioningPayload
    image_ref: str
    request: RuntimeProvisionRequest


class ProvisioningEventHandler:
    def __init__(
        self,
        *,
        uow: ProcessPendingOnceUnitOfWork,
        image_resolver: RuntimeImageResolverPort,
        provisioner: RuntimeProvisionerPort,
        runtime_inspector: RuntimeInspectorPort,
        policy: ProvisioningPolicy,
        transition: Callable[..., object],
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._uow = uow
        self._image_resolver = image_resolver
        self._provisioner = provisioner
        self._runtime_inspector = runtime_inspector
        self._policy = policy
        self._transition = transition
        self._monotonic = monotonic
        self._sleep = sleep

    def handle(self, event: PendingProvisioningEvent) -> _EventOutcome:
        try:
            payload = ProvisioningPayload.model_validate(event.payload)
        except ValidationError:
            self._mark_terminal(event, "INVALID_OUTBOX_PAYLOAD")
            return "failed"

        try:
            context = self._build_context(event=event, payload=payload)
            self._trace_requested(context)
            result = self._provisioner.provision(context.request)
            if result.status == "failed":
                return self._handle_failed_result(context=context, result=result)
            return self._handle_accepted_result(context=context, result=result)
        except _EXPECTED_EVENT_ERRORS as exc:
            logger.exception(
                "provisioning outbox event failed",
                extra={
                    "event": "provisioning_outbox_event_failed",
                    "outbox_event_id": str(event.outbox_event_id),
                    "session_id": str(event.session_id),
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            self._mark_terminal(event, "INVALID_OUTBOX_PAYLOAD")
            return "failed"

    def _build_context(
        self, *, event: PendingProvisioningEvent, payload: ProvisioningPayload
    ) -> _ProvisioningContext:
        lab_binding = self._uow.lab.get_runtime_binding(
            lab_id=payload.lab_id,
            lab_version_id=payload.lab_version_id,
        )
        image_ref = self._image_resolver.resolve(
            lab_slug=lab_binding.lab_slug,
            lab_version=lab_binding.lab_version,
        )
        idempotency_key = build_provision_request_idempotency_key(
            session_id=event.session_id,
            outbox_event_id=event.outbox_event_id,
        )
        request = RuntimeProvisionRequest(
            session_id=event.session_id,
            lab_id=payload.lab_id,
            lab_version_id=payload.lab_version_id,
            image_ref=image_ref,
            metadata={
                "outbox_event_id": str(event.outbox_event_id),
                "attempt_count": event.attempt_count,
                "requested_by": "control-plane-outbox-worker",
                "idempotency_key": idempotency_key,
            },
        )
        return _ProvisioningContext(
            event=event,
            payload=payload,
            image_ref=image_ref,
            request=request,
        )

    def _handle_accepted_result(
        self, *, context: _ProvisioningContext, result: ProvisionResult
    ) -> _EventOutcome:
        runtime_id = result.runtime_id
        if runtime_id is None or not runtime_id.strip():
            self._fail_session(context=context, reason_code="MISSING_RUNTIME_ID")
            return "failed"

        inspection = self._wait_until_ready(
            session_id=context.event.session_id,
            runtime_id=runtime_id,
            attempt_count=context.event.attempt_count,
        )
        if not inspection.ready:
            return self._mark_pending(
                context=context,
                result=result,
                inspection=inspection.last_result,
            )

        current_session = self._get_current_session(context.event.session_id)
        if current_session is None:
            self._mark_terminal(context.event, "Provisioning race: SESSION_NOT_FOUND")
            return "failed"
        if current_session.state in _TERMINAL_SESSION_STATES:
            self._enqueue_terminal_race_cleanup(
                context=context,
                runtime_id=runtime_id,
                terminal_state=current_session.state,
            )
            return "succeeded"

        base_url = _detail_string(result, "base_url")
        if base_url is None or not base_url.strip():
            self._fail_session(context=context, reason_code="MISSING_BASE_URL")
            return "failed"

        self._activate_session(
            context=context,
            runtime_id=runtime_id,
            base_url=base_url,
        )
        return "succeeded"

    def _handle_failed_result(
        self, *, context: _ProvisioningContext, result: ProvisionResult
    ) -> _EventOutcome:
        reason_code = result.reason_code or "PROVISIONING_FAILED"
        details = result.details or {}
        self._mark_terminal(
            context.event,
            f"Provisioning failed: {reason_code}",
        )
        self._transition(
            session_id=context.event.session_id,
            trigger=Trigger.PROVISIONING_FAILED,
            actor="orchestrator_worker",
            metadata={
                "outbox_event_id": str(context.event.outbox_event_id),
                "reason_code": reason_code,
                "retryable": True,
                "k8s_namespace": details.get("k8s_namespace"),
                "pod_name": details.get("pod_name"),
                "image_ref": context.request.image_ref,
                "apply_error": details.get("apply_error"),
                "k8s_event_excerpt": details.get("k8s_event_excerpt"),
            },
            idempotency_key=build_provisioning_failed_transition_idempotency_key(
                session_id=context.event.session_id,
                outbox_event_id=context.event.outbox_event_id,
            ),
            uow=self._uow.lifecycle_uow,
        )
        apply_error = _detail_string(result, "apply_error")
        self._upsert_binding(
            session_id=context.event.session_id,
            base_url=None,
            status="failed",
            last_error=apply_error or reason_code,
        )
        self._trace_failed(context=context, result=result, reason_code=reason_code)
        logger.warning(
            "session provisioning failed",
            extra={
                "event": "session_provisioning_failed",
                "session_id": str(context.event.session_id),
                "outbox_event_id": str(context.event.outbox_event_id),
                "reason_code": reason_code,
                "retryable": True,
                "k8s_namespace": details.get("k8s_namespace"),
                "pod_name": details.get("pod_name"),
                "image_ref": context.request.image_ref,
                "apply_error": details.get("apply_error"),
                "k8s_event_excerpt": details.get("k8s_event_excerpt"),
            },
        )
        return "failed"

    def _wait_until_ready(
        self,
        *,
        session_id: UUID,
        runtime_id: str,
        attempt_count: int,
    ) -> "_ReadinessOutcome":
        deadline = self._monotonic() + self._policy.readiness_timeout_seconds
        request = RuntimeInspectorRequest(
            session_id=session_id,
            runtime_id=runtime_id,
        )
        last_result: RuntimeInspectorResult | None = None
        while self._monotonic() < deadline:
            try:
                last_result = self._runtime_inspector.inspect(request=request)
                if (
                    last_result.exists
                    and last_result.phase == "Running"
                    and last_result.ready is True
                ):
                    return _ReadinessOutcome(ready=True, last_result=last_result)
            except Exception as exc:
                logger.warning(
                    "runtime readiness inspect failed",
                    extra={
                        "event": "runtime_readiness_inspect_failed",
                        "session_id": str(session_id),
                        "runtime_id": runtime_id,
                        "attempt_count": attempt_count,
                        "error": str(exc),
                    },
                )
            self._sleep(self._policy.readiness_poll_interval_seconds)
        return _ReadinessOutcome(ready=False, last_result=last_result)

    def _mark_pending(
        self,
        *,
        context: _ProvisioningContext,
        result: ProvisionResult,
        inspection: RuntimeInspectorResult | None,
    ) -> _EventOutcome:
        phase = inspection.phase if inspection is not None else None
        ready = inspection.ready if inspection is not None else None
        exists = inspection.exists if inspection is not None else None
        reason_code = "RUNTIME_NOT_READY"
        error_message = f"{reason_code}: phase={phase} ready={ready} exists={exists}"
        self._uow.outbox.mark_retryable_failure(
            outbox_event_id=context.event.outbox_event_id,
            error_message=error_message,
            backoff_seconds=self._policy.retry_backoff_seconds,
            failed_at=datetime.now(timezone.utc),
        )
        self._upsert_binding(
            session_id=context.event.session_id,
            base_url=_detail_string(result, "base_url"),
            status="provisioning",
            last_error=error_message,
        )
        append_runtime_trace(
            uow=self._uow.lifecycle_uow,
            session_id=context.event.session_id,
            event_type="RUNTIME_PROVISION_PENDING",
            source="orchestrator_service",
            payload={
                "reason_code": reason_code,
                "phase": phase,
                "ready": ready,
                "exists": exists,
                "outbox_event_id": str(context.event.outbox_event_id),
                "attempt_count": context.event.attempt_count,
            },
            lab_id=context.payload.lab_id,
            lab_version_id=context.payload.lab_version_id,
        )
        return "retried"

    def _activate_session(
        self, *, context: _ProvisioningContext, runtime_id: str, base_url: str
    ) -> None:
        activated_at = datetime.now(timezone.utc)
        self._uow.outbox.mark_processed(
            outbox_event_id=context.event.outbox_event_id,
            processed_at=activated_at,
        )
        self._transition(
            session_id=context.event.session_id,
            trigger=Trigger.PROVISIONING_SUCCEEDED,
            actor="orchestrator_worker",
            metadata={
                "outbox_event_id": str(context.event.outbox_event_id),
                "runtime_id": runtime_id,
            },
            idempotency_key=build_provisioning_succeeded_transition_idempotency_key(
                session_id=context.event.session_id,
                outbox_event_id=context.event.outbox_event_id,
            ),
            uow=self._uow.lifecycle_uow,
            runtime_id=runtime_id,
        )
        initialize_session_objectives(
            session_id=context.event.session_id,
            lab_version_id=context.payload.lab_version_id,
            template_reader=self._uow.objective_templates,
            objective_writer=self._uow.session_objectives,
        )
        initialize_session_hints(
            session_id=context.event.session_id,
            lab_version_id=context.payload.lab_version_id,
            activated_at=activated_at,
            template_reader=self._uow.hint_templates,
            hint_writer=self._uow.session_hints,
        )
        self._upsert_binding(
            session_id=context.event.session_id,
            base_url=base_url,
            status="ready",
            last_error=None,
        )
        append_runtime_trace(
            uow=self._uow.lifecycle_uow,
            session_id=context.event.session_id,
            event_type="RUNTIME_PROVISION_ACCEPTED",
            source="orchestrator_service",
            payload=self._request_trace_payload(context),
            lab_id=context.payload.lab_id,
            lab_version_id=context.payload.lab_version_id,
        )

    def _fail_session(self, *, context: _ProvisioningContext, reason_code: str) -> None:
        self._mark_terminal(
            context.event,
            f"Provisioning failed: {reason_code}",
        )
        self._transition(
            session_id=context.event.session_id,
            trigger=Trigger.PROVISIONING_FAILED,
            actor="orchestrator_worker",
            metadata={
                "outbox_event_id": str(context.event.outbox_event_id),
                "reason_code": reason_code,
            },
            idempotency_key=build_provisioning_failed_transition_idempotency_key(
                session_id=context.event.session_id,
                outbox_event_id=context.event.outbox_event_id,
            ),
            uow=self._uow.lifecycle_uow,
        )

    def _enqueue_terminal_race_cleanup(
        self,
        *,
        context: _ProvisioningContext,
        runtime_id: str,
        terminal_state: SessionState,
    ) -> None:
        now = datetime.now(timezone.utc)
        self._uow.outbox.mark_processed(
            outbox_event_id=context.event.outbox_event_id,
            processed_at=now,
        )
        with self._uow.lifecycle_uow.transaction():
            self._uow.lifecycle_uow.outbox.enqueue_for_cleanup(
                session_id=context.event.session_id,
                runtime_id=runtime_id,
                terminal_state=terminal_state.value,
                reason_code="PROVISIONED_AFTER_TERMINAL",
                requested_at=now,
            )

    def _get_current_session(self, session_id: UUID) -> SessionRow | None:
        with self._uow.lifecycle_uow.transaction():
            return self._uow.lifecycle_uow.sessions.get_for_update(
                session_id=session_id
            )

    def _upsert_binding(
        self,
        *,
        session_id: UUID,
        base_url: str | None,
        status: Literal["provisioning", "ready", "failed"],
        last_error: str | None,
    ) -> None:
        self._uow.runtime_binding.upsert_runtime_binding(
            input=UpsertSessionRuntimeBindingInput(
                session_id=session_id,
                runtime_kind="k8s_pod",
                base_url=base_url,
                auth_token_ref=None,
                status=status,
                last_error=last_error,
            )
        )

    def _mark_terminal(
        self, event: PendingProvisioningEvent, error_message: str
    ) -> None:
        self._uow.outbox.mark_terminal_failure(
            outbox_event_id=event.outbox_event_id,
            error_message=error_message,
            failed_at=datetime.now(timezone.utc),
        )

    def _trace_requested(self, context: _ProvisioningContext) -> None:
        append_runtime_trace(
            uow=self._uow.lifecycle_uow,
            session_id=context.event.session_id,
            event_type="RUNTIME_PROVISION_REQUESTED",
            source="orchestrator_service",
            payload=self._request_trace_payload(context),
            lab_id=context.payload.lab_id,
            lab_version_id=context.payload.lab_version_id,
        )

    def _trace_failed(
        self,
        *,
        context: _ProvisioningContext,
        result: ProvisionResult,
        reason_code: str,
    ) -> None:
        details = result.details or {}
        append_runtime_trace(
            uow=self._uow.lifecycle_uow,
            session_id=context.event.session_id,
            event_type="RUNTIME_PROVISION_FAILED",
            source="orchestrator_service",
            payload={
                **self._request_trace_payload(context),
                "reason_code": reason_code,
                "apply_error": details.get("apply_error"),
                "pod_name": details.get("pod_name"),
            },
            lab_id=context.payload.lab_id,
            lab_version_id=context.payload.lab_version_id,
        )

    @staticmethod
    def _request_trace_payload(
        context: _ProvisioningContext,
    ) -> dict[str, object]:
        return {
            "runtime_kind": "k8s_pod",
            "namespace": "runtime-pool",
            "image_ref": context.image_ref,
            "outbox_event_id": str(context.event.outbox_event_id),
            "attempt_count": context.event.attempt_count,
            "requested_by": "control-plane-outbox-worker",
            "idempotency_key": context.request.metadata["idempotency_key"],
        }


@dataclass(frozen=True)
class _ReadinessOutcome:
    ready: bool
    last_result: RuntimeInspectorResult | None


def _detail_string(result: ProvisionResult, key: str) -> str | None:
    value = (result.details or {}).get(key)
    return value if isinstance(value, str) else None


def process_provisioning_batch(
    *,
    uow: ProcessPendingOnceUnitOfWork,
    image_resolver: RuntimeImageResolverPort,
    provisioner: RuntimeProvisionerPort,
    runtime_inspector: RuntimeInspectorPort,
    policy: ProvisioningPolicy,
    transition: Callable[..., object],
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> ProcessPendingOnceResult:
    counts = _ProvisioningCounts()
    handler = ProvisioningEventHandler(
        uow=uow,
        image_resolver=image_resolver,
        provisioner=provisioner,
        runtime_inspector=runtime_inspector,
        policy=policy,
        transition=transition,
        monotonic=monotonic,
        sleep=sleep,
    )
    try:
        with uow.transaction():
            for event in uow.outbox.claim_pending_provisioning():
                counts.claimed += 1
                counts.record(handler.handle(event))
    except Exception:
        logger.exception("process_pending_once batch failed")

    result = counts.result()
    logger.info(
        "orchestrator provisioning batch completed",
        extra={
            "event": "orchestrator_provisioning_batch_completed",
            "claimed_count": result.claimed_count,
            "succeeded_count": result.succeeded_count,
            "failed_count": result.failed_count,
            "retried_count": result.retried_count,
        },
    )
    return result
