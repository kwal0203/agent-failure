from dataclasses import dataclass


@dataclass(frozen=True)
class K8sProvisionerConfig:
    namespace: str = "runtime-pool"
    kubectl_bin: str = "kubectl"

    run_as_non_root: bool = True
    allow_privilege_escalation: bool = False
    drop_all_capabilities: bool = True
    read_only_root_filesystem: bool = True
    seccomp_profile_type: str = "RuntimeDefault"
    automount_service_account_token: bool = False

    cpu_request: str = "250m"
    memory_request: str = "256Mi"
    cpu_limit: str = "1000m"
    memory_limit: str = "1Gi"

    tmp_volume_name: str = "tmp"
    tmp_mount_path: str = "/tmp"

    image_pull_secret_name: str | None = "ghcr-pull"


@dataclass(frozen=True)
class K8sCleanupConfig:
    namespace: str = "runtime-pool"
    kubectl_bin: str = "kubectl"


@dataclass(frozen=True)
class K8sRuntimeInspectorConfig:
    namespace: str = "runtime-pool"
    kubectl_bin: str = "kubectl"
