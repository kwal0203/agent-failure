from apps.control_plane.src.application.orchestrator.ports import (
    ProcessPendingOnceUnitOfWork,
)
from apps.control_plane.src.application.orchestrator.types import (
    RuntimeProvisionRequest,
)
from apps.control_plane.src.application.session_lifecycle.service import (
    transition_session,
)
from apps.control_plane.src.domain.session_lifecycle.state_machine import Trigger

from .ports import RuntimeProvisionerPort, RuntimeImageResolverPort
from .types import ProcessPendingOnceResult

from uuid import UUID
from datetime import datetime, timezone

from apps.control_plane.src.infrastructure.runtime.errors import (
    ImageNotFoundError,
    ImageRevokedError,
    InvalidImageLockError,
    DefaultSelectionError,
)
from apps.control_plane.src.application.session_lifecycle.errors import (
    SessionNotFound,
    InvalidTransition,
    TransitionValidationError,
)
from apps.control_plane.src.infrastructure.persistence.errors import (
    DataIntegrityError,
    StateMismatch,
)

import logging

logger = logging.getLogger(__name__)


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
                            "outbox_event_id": outbox_event_id,
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
