import logging
from typing import Mapping, cast

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from apps.control_plane.src.application.orchestrator.ports import RuntimeProvisionerPort
from apps.control_plane.src.application.orchestrator.types import (
    ProvisionResult,
    RuntimeProvisionRequest,
)
from apps.control_plane.src.infrastructure.config.settings import (
    RuntimePodEnvSettings,
    get_runtime_pod_env_settings,
)

from .k8s_client import create_core_v1_api
from .types import K8sProvisionerConfig, SESSION_LABEL

logger = logging.getLogger(__name__)

SERVER_SIDE_APPLY_CONTENT_TYPE = "application/apply-patch+yaml"


class K8sRuntimeProvisioner(RuntimeProvisionerPort):
    def __init__(
        self,
        config: K8sProvisionerConfig | None = None,
        runtime_env: RuntimePodEnvSettings | None = None,
        core_api: client.CoreV1Api | None = None,
    ) -> None:
        self._config = config or K8sProvisionerConfig()
        self._runtime_env = runtime_env or get_runtime_pod_env_settings()
        self._configured_core_api = core_api

    @property
    def _core_api(self) -> client.CoreV1Api:
        if self._configured_core_api is None:
            self._configured_core_api = create_core_v1_api()
        return self._configured_core_api

    def provision(self, request: RuntimeProvisionRequest) -> ProvisionResult:
        pod_name = f"session-{str(request.session_id)[:8]}"
        # Keep service/pod naming aligned with Kubernetes DNS-label constraints if
        # this naming format evolves.
        pod = self._build_pod(
            pod_name=pod_name,
            image_ref=request.image_ref,
            metadata=request.metadata,
            request=request,
        )

        try:
            applied_pod = self._apply_pod(pod_name=pod_name, pod=pod)
            pod_uid = (
                str(applied_pod.metadata.uid)
                if applied_pod.metadata and applied_pod.metadata.uid
                else ""
            )
            if not pod_uid:
                raise RuntimeError(f"Kubernetes Pod {pod_name!r} has no UID")

            service = self._build_service(
                service_name=pod_name,
                pod_name=pod_name,
                pod_uid=pod_uid,
                request=request,
            )
            self._apply_service(service_name=pod_name, service=service)
            return ProvisionResult(
                status="accepted",
                runtime_id=pod_name,
                details={
                    "namespace": self._config.namespace,
                    "base_url": (
                        f"http://{pod_name}.{self._config.namespace}"
                        ".svc.cluster.local:8000"
                    ),
                },
            )
        except ApiException as exc:
            self._best_effort_cleanup(session_id=str(request.session_id))
            error_text = self._api_error_text(exc)
            return ProvisionResult(
                status="failed",
                reason_code="K8S_APPLY_FAILED",
                details={
                    "k8s_namespace": self._config.namespace,
                    "pod_name": pod_name,
                    "image_ref": request.image_ref,
                    "apply_error": error_text[:512],
                    "k8s_event_excerpt": error_text[:512],
                },
            )
        except Exception as exc:
            self._best_effort_cleanup(session_id=str(request.session_id))
            error_text = str(exc).strip() or exc.__class__.__name__
            return ProvisionResult(
                status="failed",
                reason_code="PROVISION_INTERNAL_ERROR",
                details={
                    "k8s_namespace": self._config.namespace,
                    "pod_name": pod_name,
                    "image_ref": request.image_ref,
                    "apply_error": error_text[:512],
                    "k8s_event_excerpt": error_text[:512],
                },
            )

    def _apply_pod(self, *, pod_name: str, pod: client.V1Pod) -> client.V1Pod:
        return cast(
            client.V1Pod,
            self._core_api.patch_namespaced_pod(
                name=pod_name,
                namespace=self._config.namespace,
                body=pod,
                field_manager=self._config.field_manager,
                force=True,
                field_validation="Strict",
                _content_type=SERVER_SIDE_APPLY_CONTENT_TYPE,
                _request_timeout=self._config.api_request_timeout_seconds,
            ),
        )

    def _apply_service(
        self, *, service_name: str, service: client.V1Service
    ) -> client.V1Service:
        return cast(
            client.V1Service,
            self._core_api.patch_namespaced_service(
                name=service_name,
                namespace=self._config.namespace,
                body=service,
                field_manager=self._config.field_manager,
                force=True,
                field_validation="Strict",
                _content_type=SERVER_SIDE_APPLY_CONTENT_TYPE,
                _request_timeout=self._config.api_request_timeout_seconds,
            ),
        )

    def _best_effort_cleanup(self, session_id: str) -> None:
        selector = f"{SESSION_LABEL}={session_id}"
        try:
            self._core_api.delete_collection_namespaced_service(
                namespace=self._config.namespace,
                label_selector=selector,
                propagation_policy="Foreground",
                _request_timeout=self._config.api_request_timeout_seconds,
            )
            self._core_api.delete_collection_namespaced_pod(
                namespace=self._config.namespace,
                label_selector=selector,
                propagation_policy="Foreground",
                _request_timeout=self._config.api_request_timeout_seconds,
            )
        except Exception:
            logger.exception(
                "Failed to clean up Kubernetes resources after provisioning error",
                extra={"session_id": session_id},
            )

    @staticmethod
    def _api_error_text(exc: ApiException) -> str:
        return (
            str(exc.body or exc.reason or exc).strip()
            or "Kubernetes API request failed"
        )

    @staticmethod
    def _resource_labels(request: RuntimeProvisionRequest) -> dict[str, str]:
        return {
            "app.kubernetes.io/name": "lab-runtime",
            "app.kubernetes.io/managed-by": "agent-failure-control-plane",
            "app.kubernetes.io/instance": f"session-{str(request.session_id)[:8]}",
            SESSION_LABEL: str(request.session_id),
            "agent-failure/lab-id": str(request.lab_id),
            "agent-failure/lab-version-id": str(request.lab_version_id),
        }

    def _build_pod(
        self,
        *,
        pod_name: str,
        image_ref: str,
        metadata: Mapping[str, object],
        request: RuntimeProvisionRequest,
    ) -> client.V1Pod:
        labels = self._resource_labels(request)
        _ = metadata

        capabilities = (
            client.V1Capabilities(drop=["ALL"])
            if self._config.drop_all_capabilities
            else None
        )
        container_security_context = client.V1SecurityContext(
            run_as_non_root=self._config.run_as_non_root,
            allow_privilege_escalation=self._config.allow_privilege_escalation,
            read_only_root_filesystem=self._config.read_only_root_filesystem,
            capabilities=capabilities,
        )

        runtime_env = [
            client.V1EnvVar(
                name="RUNTIME_SHARED_TOKEN",
                value_from=client.V1EnvVarSource(
                    secret_key_ref=client.V1SecretKeySelector(
                        name=self._config.runtime_secret_name,
                        key=self._config.runtime_shared_token_secret_key,
                        optional=False,
                    )
                ),
            ),
            client.V1EnvVar(
                name="MODEL_CLIENT_MODE",
                value=self._runtime_env.model_client_mode,
            ),
            client.V1EnvVar(
                name="PROVIDER_ENDPOINT",
                value=self._runtime_env.provider_endpoint,
            ),
            client.V1EnvVar(name="MODEL_NAME", value=self._runtime_env.model_name),
            client.V1EnvVar(name="RUNTIME_SESSION_ID", value=str(request.session_id)),
        ]
        if self._runtime_env.model_client_mode == "gateway":
            runtime_env.append(
                client.V1EnvVar(
                    name="OPENROUTER_API_KEY",
                    value_from=client.V1EnvVarSource(
                        secret_key_ref=client.V1SecretKeySelector(
                            name=self._config.runtime_secret_name,
                            key=self._config.openrouter_api_key_secret_key,
                            optional=False,
                        )
                    ),
                )
            )

        volumes: list[client.V1Volume] | None = None
        volume_mounts: list[client.V1VolumeMount] | None = None
        if self._config.read_only_root_filesystem:
            volumes = [
                client.V1Volume(
                    name=self._config.tmp_volume_name,
                    empty_dir=client.V1EmptyDirVolumeSource(),
                )
            ]
            volume_mounts = [
                client.V1VolumeMount(
                    name=self._config.tmp_volume_name,
                    mount_path=self._config.tmp_mount_path,
                )
            ]

        image_pull_secrets = (
            [client.V1LocalObjectReference(name=self._config.image_pull_secret_name)]
            if self._config.image_pull_secret_name
            else None
        )
        container = client.V1Container(
            name="runtime",
            image=image_ref,
            image_pull_policy="IfNotPresent",
            security_context=container_security_context,
            env=runtime_env,
            resources=client.V1ResourceRequirements(
                requests={
                    "cpu": self._config.cpu_request,
                    "memory": self._config.memory_request,
                    "ephemeral-storage": "512Mi",
                },
                limits={
                    "cpu": self._config.cpu_limit,
                    "memory": self._config.memory_limit,
                    "ephemeral-storage": "1Gi",
                },
            ),
            volume_mounts=volume_mounts,
        )
        return client.V1Pod(
            api_version="v1",
            kind="Pod",
            metadata=client.V1ObjectMeta(
                name=pod_name,
                namespace=self._config.namespace,
                labels=labels,
            ),
            spec=client.V1PodSpec(
                automount_service_account_token=(
                    self._config.automount_service_account_token
                ),
                restart_policy="Never",
                security_context=client.V1PodSecurityContext(
                    seccomp_profile=client.V1SeccompProfile(
                        type=self._config.seccomp_profile_type
                    )
                ),
                containers=[container],
                volumes=volumes,
                image_pull_secrets=image_pull_secrets,
            ),
        )

    def _build_service(
        self,
        *,
        service_name: str,
        pod_name: str,
        pod_uid: str,
        request: RuntimeProvisionRequest,
    ) -> client.V1Service:
        labels = self._resource_labels(request)
        return client.V1Service(
            api_version="v1",
            kind="Service",
            metadata=client.V1ObjectMeta(
                name=service_name,
                namespace=self._config.namespace,
                labels=labels,
                owner_references=[
                    client.V1OwnerReference(
                        api_version="v1",
                        kind="Pod",
                        name=pod_name,
                        uid=pod_uid,
                        controller=True,
                        block_owner_deletion=False,
                    )
                ],
            ),
            spec=client.V1ServiceSpec(
                selector={SESSION_LABEL: str(request.session_id)},
                ports=[
                    client.V1ServicePort(
                        name="http",
                        port=8000,
                        target_port=8000,
                    )
                ],
                type="ClusterIP",
            ),
        )
