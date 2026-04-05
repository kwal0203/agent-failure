import logging
import os
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
from apps.control_plane.src.infrastructure.orchestrator.k8s_runtime_inspector import (
    K8sRuntimeInspector,
)
from apps.control_plane.src.infrastructure.persistence.worker_heartbeat_repository import (
    SQLAlchemyWorkerHeartbeatRepository,
)

from dotenv import load_dotenv

logger = logging.getLogger(__name__)
REPO_ROOT = Path(__file__).resolve().parents[5]
DOTENV_PATH = REPO_ROOT / ".env"


def _load_worker_env() -> None:
    # Load repo-root .env regardless of current working directory.
    load_dotenv(dotenv_path=DOTENV_PATH, override=False)

    # Keep backward compatibility with existing local setups that only define
    # RUNTIME_AUTH_TOKEN while k8s runtime pods need RUNTIME_SHARED_TOKEN.
    if not os.getenv("RUNTIME_SHARED_TOKEN") and os.getenv("RUNTIME_AUTH_TOKEN"):
        os.environ["RUNTIME_SHARED_TOKEN"] = os.environ["RUNTIME_AUTH_TOKEN"] or ""
        logger.info(
            "provisioning worker env: using RUNTIME_AUTH_TOKEN as RUNTIME_SHARED_TOKEN fallback"
        )

    _validate_required_env()


def _validate_required_env() -> None:
    model_mode = (os.getenv("MODEL_CLIENT_MODE") or "").strip() or "gateway"

    required = ["RUNTIME_SHARED_TOKEN", "MODEL_CLIENT_MODE", "MODEL_NAME"]
    if model_mode == "gateway":
        required.extend(["PROVIDER_ENDPOINT", "OPENROUTER_API_KEY"])

    missing = [name for name in required if not (os.getenv(name) or "").strip()]
    if missing:
        joined = ", ".join(sorted(missing))
        raise RuntimeError(
            f"Missing required env for provisioning worker runtime pods: {joined}"
        )


def _build_dependencies() -> tuple[
    SQLAlchemyProcessPendingOnceUnitOfWork,
    RuntimeImageResolver,
    K8sRuntimeProvisioner,
    SQLAlchemyWorkerHeartbeatRepository,
    K8sRuntimeInspector,
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
    runtime_inspector = K8sRuntimeInspector()
    return uow, resolver, provisioner, heartbeat_repo, runtime_inspector


def run_once() -> None:
    uow, resolver, provisioner, heartbeat_repo, runtime_inspector = (
        _build_dependencies()
    )
    ts = datetime.now(timezone.utc)
    heartbeat_repo.record_tick(worker_name="provisioning_worker", at=ts)

    try:
        result = process_pending_once(
            uow=uow,
            image_resolver=resolver,
            provisioner=provisioner,
            runtime_inspector=runtime_inspector,
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
            logger.exception("provisioning worker tick failed")
        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _load_worker_env()
    run_forever(poll_interval_seconds=10.0)
