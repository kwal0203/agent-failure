from dataclasses import dataclass


SESSION_LABEL = "agent-failure/session-id"


@dataclass(frozen=True)
class K8sProvisionerConfig:
    namespace: str = "runtime-pool"
    field_manager: str = "agent-failure-control-plane"
    api_request_timeout_seconds: float = 30.0
    runtime_secret_name: str = "runtime-secrets"
    runtime_shared_token_secret_key: str = "RUNTIME_SHARED_TOKEN"
    openrouter_api_key_secret_key: str = "OPENROUTER_API_KEY"

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
    api_request_timeout_seconds: float = 30.0
    deletion_timeout_seconds: float = 30.0
    deletion_poll_interval_seconds: float = 0.25


@dataclass(frozen=True)
class K8sRuntimeInspectorConfig:
    namespace: str = "runtime-pool"
    api_request_timeout_seconds: float = 30.0
