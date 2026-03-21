from dataclasses import dataclass


@dataclass(frozen=True)
class K8sProvisionerConfig:
    namespace: str = "runtime-pool"
    kubectl_bin: str = "kubectl"


@dataclass(frozen=True)
class K8sCleanupConfig:
    namespace: str = "runtime-pool"
    kubectl_bin: str = "kubectl"


@dataclass(frozen=True)
class K8sRuntimeInspectorConfig:
    namespace: str = "runtime-pool"
    kubectl_bin: str = "kubectl"
