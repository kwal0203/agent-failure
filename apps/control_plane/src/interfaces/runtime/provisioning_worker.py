import logging
import time
from pathlib import Path

from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.application.orchestrator.service import process_pending_once
from apps.control_plane.src.infrastructure.persistence.unit_of_work_outbox_pending import (
    SQLAlchemyProcessPendingOnceUnitOfWork,
)
from apps.control_plane.src.infrastructure.runtime.image_resolver import (
    RuntimeImageResolver,
)
from apps.control_plane.src.infrastructure.orchestrator.k8s_provisioner import (
    K8sRuntimeProvisioner,
)

logger = logging.getLogger(__name__)


def _build_dependencies() -> tuple[
    SQLAlchemyProcessPendingOnceUnitOfWork, RuntimeImageResolver, K8sRuntimeProvisioner
]:
    uow = SQLAlchemyProcessPendingOnceUnitOfWork(session_factory=SessionFactory)
    resolver = RuntimeImageResolver(
        lock_file=Path("deploy/k8s/staging/runtime-image.lock"),
        selection_file=Path("deploy/k8s/staging/runtime-image-selection.yaml"),
    )
    provisioner = K8sRuntimeProvisioner()
    return uow, resolver, provisioner


def run_once() -> None:
    uow, resolver, provisioner = _build_dependencies()
    result = process_pending_once(
        uow=uow, image_resolver=resolver, provisioner=provisioner
    )
    logger.info(
        "provisioning worker tick claimed=%s succeeded=%s failed=%s retried=%s",
        result.claimed_count,
        result.succeeded_count,
        result.failed_count,
        result.retried_count,
    )


def run_forever(poll_interval_seconds: float = 1.0) -> None:
    # TODO(P0-E1 follow-up): harden worker loop with try/except around run_once
    # so unexpected per-tick exceptions are logged and do not kill the process.
    while True:
        run_once()
        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever(poll_interval_seconds=10.0)
