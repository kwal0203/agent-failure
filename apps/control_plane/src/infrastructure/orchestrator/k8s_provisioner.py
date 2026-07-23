import json
import logging
import subprocess
from typing import Any, Mapping, cast

from apps.control_plane.src.application.orchestrator.ports import RuntimeProvisionerPort
from apps.control_plane.src.application.orchestrator.types import (
    ProvisionResult,
    RuntimeProvisionRequest,
)
from apps.control_plane.src.infrastructure.config.settings import (
    RuntimePodEnvSettings,
    get_runtime_pod_env_settings,
)

from .types import K8sProvisionerConfig, SESSION_LABEL

logger = logging.getLogger(__name__)


class K8sRuntimeProvisioner(RuntimeProvisionerPort):
    def __init__(
        self,
        config: K8sProvisionerConfig | None = None,
        runtime_env: RuntimePodEnvSettings | None = None,
    ) -> None:
        self._config = config or K8sProvisionerConfig()
        self._runtime_env = runtime_env or get_runtime_pod_env_settings()

    def provision(self, request: RuntimeProvisionRequest) -> ProvisionResult:
        pod_name = f"session-{str(request.session_id)[:8]}"
        # TODO(runtime-provisioning): Keep service/pod naming aligned with k8s DNS
        # label length constraints (63 chars) if naming format evolves.

        manifest = self._build_pod_manifest(
            pod_name=pod_name,
            image_ref=request.image_ref,
            metadata=request.metadata,
            request=request,
        )

        try:
            self._kubectl_apply(manifest)
            pod_uid = self._kubectl_get_pod_uid(pod_name)
            service_manifest = self._build_service_manifest(
                service_name=pod_name,
                pod_name=pod_name,
                pod_uid=pod_uid,
                request=request,
            )
            self._kubectl_apply(service_manifest)
            return ProvisionResult(
                status="accepted",
                runtime_id=pod_name,
                details={
                    "namespace": self._config.namespace,
                    "base_url": f"http://{pod_name}.{self._config.namespace}.svc.cluster.local:8000",
                },
            )

        except subprocess.CalledProcessError as exc:
            self._best_effort_cleanup(session_id=str(request.session_id))
            stderr = (exc.stderr or "").strip()
            excerpt = " | ".join(stderr.splitlines()[:3])[:512]
            return ProvisionResult(
                status="failed",
                reason_code="K8S_APPLY_FAILED",
                details={
                    "k8s_namespace": self._config.namespace,
                    "pod_name": pod_name,
                    "image_ref": request.image_ref,
                    "apply_error": stderr.splitlines()[0]
                    if stderr
                    else "kubectl apply failed",
                    "k8s_event_excerpt": excerpt or "kubectl apply failed",
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

    def _kubectl_apply(self, manifest: dict[str, object]) -> None:
        subprocess.run(
            [self._config.kubectl_bin, "apply", "-f", "-"],
            input=json.dumps(manifest),
            text=True,
            check=True,
            capture_output=True,
        )

    def _kubectl_get_pod_uid(self, pod_name: str) -> str:
        result = subprocess.run(
            [
                self._config.kubectl_bin,
                "-n",
                self._config.namespace,
                "get",
                "pod",
                pod_name,
                "-o",
                "jsonpath={.metadata.uid}",
            ],
            text=True,
            check=True,
            capture_output=True,
        )
        pod_uid = result.stdout.strip()
        if not pod_uid:
            raise RuntimeError(f"Kubernetes Pod {pod_name!r} has no UID")
        return pod_uid

    def _best_effort_cleanup(self, session_id: str) -> None:
        try:
            subprocess.run(
                [
                    self._config.kubectl_bin,
                    "-n",
                    self._config.namespace,
                    "delete",
                    "pod,service",
                    "-l",
                    f"{SESSION_LABEL}={session_id}",
                    "--ignore-not-found=true",
                    "--wait=true",
                    "--timeout=30s",
                ],
                text=True,
                check=True,
                capture_output=True,
            )
        except Exception:
            logger.exception(
                "Failed to clean up Kubernetes resources after provisioning error",
                extra={"session_id": session_id},
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

    def _build_pod_manifest(
        self,
        *,
        pod_name: str,
        image_ref: str,
        metadata: Mapping[str, object],
        request: RuntimeProvisionRequest,
    ) -> dict[str, object]:
        labels = self._resource_labels(request)

        _ = metadata

        container_security_context: dict[str, object] = {
            "runAsNonRoot": self._config.run_as_non_root,
            "allowPrivilegeEscalation": self._config.allow_privilege_escalation,
            "readOnlyRootFilesystem": self._config.read_only_root_filesystem,
        }

        runtime_env: list[dict[str, object]] = [
            {
                "name": "RUNTIME_SHARED_TOKEN",
                "valueFrom": {
                    "secretKeyRef": {
                        "name": self._config.runtime_secret_name,
                        "key": self._config.runtime_shared_token_secret_key,
                        "optional": False,
                    }
                },
            },
            {
                "name": "MODEL_CLIENT_MODE",
                "value": self._runtime_env.model_client_mode,
            },
            {
                "name": "PROVIDER_ENDPOINT",
                "value": self._runtime_env.provider_endpoint,
            },
            {
                "name": "MODEL_NAME",
                "value": self._runtime_env.model_name,
            },
            {"name": "LAB_DIFFICULTY", "value": request.lab_difficulty},
        ]
        if self._runtime_env.model_client_mode == "gateway":
            runtime_env.append(
                {
                    "name": "OPENROUTER_API_KEY",
                    "valueFrom": {
                        "secretKeyRef": {
                            "name": self._config.runtime_secret_name,
                            "key": self._config.openrouter_api_key_secret_key,
                            "optional": False,
                        }
                    },
                }
            )
        if self._config.drop_all_capabilities:
            container_security_context["capabilities"] = {"drop": ["ALL"]}

        spec: dict[str, object] = {
            "automountServiceAccountToken": self._config.automount_service_account_token,
            "restartPolicy": "Never",
            "securityContext": {
                "seccompProfile": {"type": self._config.seccomp_profile_type}
            },
            "containers": [
                {
                    "name": "runtime",
                    "image": image_ref,
                    "imagePullPolicy": "IfNotPresent",
                    "securityContext": container_security_context,
                    "env": runtime_env,
                    "resources": {
                        "requests": {
                            "cpu": self._config.cpu_request,
                            "memory": self._config.memory_request,
                            "ephemeral-storage": "512Mi",
                        },
                        "limits": {
                            "cpu": self._config.cpu_limit,
                            "memory": self._config.memory_limit,
                            "ephemeral-storage": "1Gi",
                        },
                    },
                }
            ],
        }

        if self._config.read_only_root_filesystem:
            spec["volumes"] = [{"name": self._config.tmp_volume_name, "emptyDir": {}}]
            container = cast(dict[str, Any], cast(list[object], spec["containers"])[0])
            container["volumeMounts"] = [
                {
                    "name": self._config.tmp_volume_name,
                    "mountPath": self._config.tmp_mount_path,
                }
            ]

        if self._config.image_pull_secret_name:
            spec["imagePullSecrets"] = [{"name": self._config.image_pull_secret_name}]

        return {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": pod_name,
                "namespace": self._config.namespace,
                "labels": labels,
            },
            "spec": spec,
        }

    def _build_service_manifest(
        self,
        *,
        service_name: str,
        pod_name: str,
        pod_uid: str,
        request: RuntimeProvisionRequest,
    ) -> dict[str, object]:
        labels = self._resource_labels(request)
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": service_name,
                "namespace": self._config.namespace,
                "labels": labels,
                "ownerReferences": [
                    {
                        "apiVersion": "v1",
                        "kind": "Pod",
                        "name": pod_name,
                        "uid": pod_uid,
                        "controller": True,
                        "blockOwnerDeletion": False,
                    }
                ],
            },
            "spec": {
                "selector": {SESSION_LABEL: str(request.session_id)},
                "ports": [{"name": "http", "port": 8000, "targetPort": 8000}],
                "type": "ClusterIP",
            },
        }
