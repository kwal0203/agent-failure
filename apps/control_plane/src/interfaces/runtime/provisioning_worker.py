import logging
import time
from pathlib import Path
from datetime import datetime, timezone

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
from apps.control_plane.src.infrastructure.persistence.worker_heartbeat_repository import (
    SQLAlchemyWorkerHeartbeatRepository,
)

logger = logging.getLogger(__name__)


def _build_dependencies() -> tuple[
    SQLAlchemyProcessPendingOnceUnitOfWork,
    RuntimeImageResolver,
    K8sRuntimeProvisioner,
    SQLAlchemyWorkerHeartbeatRepository,
]:
    uow = SQLAlchemyProcessPendingOnceUnitOfWork(session_factory=SessionFactory)
    resolver = RuntimeImageResolver(
        lock_file=Path("deploy/k8s/staging/runtime-image.lock"),
        selection_file=Path("deploy/k8s/staging/runtime-image-selection.yaml"),
    )
    provisioner = K8sRuntimeProvisioner()
    # NOTE(P2-EA-T4): This is a pragmatic shortcut: the worker directly instantiates
    # an infrastructure heartbeat adapter. Long-term, heartbeat writes should be
    # modeled as an application port and composed into the worker UoW so tick
    # bookkeeping and orchestration outcomes share one transactional boundary.
    heartbeat_repo = SQLAlchemyWorkerHeartbeatRepository()
    return uow, resolver, provisioner, heartbeat_repo


def run_once() -> None:
    uow, resolver, provisioner, heartbeat_repo = _build_dependencies()
    ts = datetime.now(timezone.utc)
    heartbeat_repo.record_tick(worker_name="provisioning_worker", at=ts)

    try:
        result = process_pending_once(
            uow=uow, image_resolver=resolver, provisioner=provisioner
        )
        heartbeat_repo.record_success(
            worker_name="provisioning_worker", at=datetime.now(timezone.utc)
        )
        logger.info(
            "provisioning worker tick claimed=%s succeeded=%s failed=%s retried=%s",
            result.claimed_count,
            result.succeeded_count,
            result.failed_count,
            result.retried_count,
        )
    except Exception as exc:
        heartbeat_repo.record_error(
            worker_name="provisioning_worker",
            at=datetime.now(timezone.utc),
            error_message=str(exc),
        )
        logger.exception("provisioning worker tick failed")
        raise


def run_forever(poll_interval_seconds: float = 1.0) -> None:
    # TODO(P0-E1 follow-up): harden worker loop with try/except around run_once
    # so unexpected per-tick exceptions are logged and do not kill the process.
    while True:
        try:
            run_once()
        except Exception:
            pass
        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever(poll_interval_seconds=10.0)
