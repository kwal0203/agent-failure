import logging
import time
from pathlib import Path

from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.application.orchestrator.service import process_pending_once
from apps.control_plane.src.application.orchestrator.policy import ProvisioningPolicy
from apps.control_plane.src.application.orchestrator.types import (
    ProcessPendingOnceResult,
)
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
from dotenv import load_dotenv
from apps.control_plane.src.application.common.observability import (
    log_fields,
    reset_correlation_id,
    set_correlation_id,
)
from apps.control_plane.src.infrastructure.config.settings import (
    get_app_env,
    get_orchestrator_settings,
    get_runtime_pod_env_settings,
)

logger = logging.getLogger(__name__)
WORKER_NAME = "provisioning_worker"
REPO_ROOT = Path(__file__).resolve().parents[5]
DOTENV_PATH = REPO_ROOT / ".env"


def _load_worker_env() -> None:
    # Load repo-root .env regardless of current working directory.
    load_dotenv(dotenv_path=DOTENV_PATH, override=False)
    _validate_required_env()


def _validate_required_env() -> None:
    settings = get_runtime_pod_env_settings()
    model_mode = settings.model_client_mode

    missing: list[str] = []
    if not settings.model_name.strip():
        missing.append("MODEL_NAME")
    if model_mode == "gateway":
        if not settings.provider_endpoint.strip():
            missing.append("PROVIDER_ENDPOINT")

    if missing:
        joined = ", ".join(sorted(missing))
        raise RuntimeError(
            f"Missing required env for provisioning worker runtime pods: {joined}"
        )


def _build_dependencies() -> tuple[
    SQLAlchemyProcessPendingOnceUnitOfWork,
    RuntimeImageResolver,
    K8sRuntimeProvisioner,
    K8sRuntimeInspector,
]:
    app_env = get_app_env()
    env_dir = "production" if app_env == "production" else "staging"
    lock_file = Path(f"deploy/k8s/{env_dir}/runtime-image.lock")
    selection_file = Path(f"deploy/k8s/{env_dir}/runtime-image-selection.yaml")

    logger.info(
        "provisioning worker runtime image config selected",
        extra={
            **log_fields(),
            "worker_name": WORKER_NAME,
            "app_env": app_env,
            "lock_file": str(lock_file),
            "selection_file": str(selection_file),
        },
    )

    uow = SQLAlchemyProcessPendingOnceUnitOfWork(session_factory=SessionFactory)
    resolver = RuntimeImageResolver(
        lock_file=lock_file,
        selection_file=selection_file,
    )
    provisioner = K8sRuntimeProvisioner()
    runtime_inspector = K8sRuntimeInspector()
    return uow, resolver, provisioner, runtime_inspector


ProvisioningWorkerDependencies = tuple[
    SQLAlchemyProcessPendingOnceUnitOfWork,
    RuntimeImageResolver,
    K8sRuntimeProvisioner,
    K8sRuntimeInspector,
]


def _build_policy() -> ProvisioningPolicy:
    settings = get_orchestrator_settings()
    return ProvisioningPolicy(
        readiness_timeout_seconds=settings.readiness_timeout_seconds,
        readiness_poll_interval_seconds=settings.readiness_poll_interval_seconds,
        retry_backoff_seconds=settings.provisioning_retry_backoff_seconds,
    )


def run_once(
    *,
    dependencies: ProvisioningWorkerDependencies | None = None,
    policy: ProvisioningPolicy | None = None,
) -> ProcessPendingOnceResult:
    uow, resolver, provisioner, runtime_inspector = (
        dependencies or _build_dependencies()
    )

    try:
        result = process_pending_once(
            uow=uow,
            image_resolver=resolver,
            provisioner=provisioner,
            runtime_inspector=runtime_inspector,
            policy=policy or _build_policy(),
        )

        if result.claimed_count > 0:
            logger.info(
                "provisioning worker tick claimed=%s succeeded=%s failed=%s retried=%s",
                result.claimed_count,
                result.succeeded_count,
                result.failed_count,
                result.retried_count,
                extra={**log_fields(), "worker_name": WORKER_NAME},
            )
        return result

    except Exception:
        logger.exception(
            "provisioning worker tick failed",
            extra={**log_fields(), "worker_name": WORKER_NAME},
        )
        raise


def run_forever(
    *,
    poll_interval_seconds: float,
) -> None:
    dependencies = _build_dependencies()
    policy = _build_policy()
    while True:
        token = set_correlation_id(None)
        try:
            run_once(
                dependencies=dependencies,
                policy=policy,
            )
        except Exception:
            logger.exception(
                "provisioning worker tick failed",
                extra={**log_fields(), "worker_name": WORKER_NAME},
            )
        finally:
            reset_correlation_id(token)
        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    _load_worker_env()
    orchestrator_settings = get_orchestrator_settings()
    run_forever(
        poll_interval_seconds=(
            orchestrator_settings.provisioning_worker_poll_interval_seconds
        ),
    )
