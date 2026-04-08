from apps.control_plane.src.application.orchestrator.ports import RuntimeProvisionerPort
from apps.control_plane.src.application.orchestrator.types import (
    ProvisionResult,
    RuntimeProvisionRequest,
)
from typing import Mapping, cast, Any

from .types import K8sProvisionerConfig

import subprocess
import json
import os


class K8sRuntimeProvisioner(RuntimeProvisionerPort):
    def __init__(self, config: K8sProvisionerConfig | None = None) -> None:
        self._config = config or K8sProvisionerConfig()

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

        service_manifest = self._build_service_manifest(
            service_name=pod_name, request=request
        )

        try:
            self._kubectl_apply(manifest)
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

    def _build_pod_manifest(
        self,
        *,
        pod_name: str,
        image_ref: str,
        metadata: Mapping[str, object],
        request: RuntimeProvisionRequest,
    ) -> dict[str, object]:
        labels = {
            "app.kubernetes.io/name": "lab-runtime",
            "agent-failure/session-id": str(request.session_id),
            "agent-failure/lab-id": str(request.lab_id),
            "agent-failure/lab-version-id": str(request.lab_version_id),
        }

        _ = metadata

        container_security_context: dict[str, object] = {
            "runAsNonRoot": self._config.run_as_non_root,
            "allowPrivilegeEscalation": self._config.allow_privilege_escalation,
            "readOnlyRootFilesystem": self._config.read_only_root_filesystem,
        }

        runtime_env: list[dict[str, object]] = [
            {
                "name": "RUNTIME_SHARED_TOKEN",
                "value": os.getenv("RUNTIME_SHARED_TOKEN", ""),
            },
            {
                "name": "MODEL_CLIENT_MODE",
                "value": os.getenv("MODEL_CLIENT_MODE", "gateway"),
            },
            {
                "name": "PROVIDER_ENDPOINT",
                "value": os.getenv(
                    "PROVIDER_ENDPOINT", "https://openrouter.ai/api/v1/chat/completions"
                ),
            },
            {
                "name": "MODEL_NAME",
                "value": os.getenv("MODEL_NAME", "deepseek/deepseek-v3.2"),
            },
            {
                "name": "OPENROUTER_API_KEY",
                "value": os.getenv("OPENROUTER_API_KEY", ""),
            },
            {"name": "LAB_DIFFICULTY", "value": request.lab_difficulty},
        ]
        # TODO(runtime-provisioning): Validate required env values before apply
        # (e.g. RUNTIME_SHARED_TOKEN, and OPENROUTER_API_KEY when gateway mode
        # is enabled) to avoid provisioning pods that are guaranteed to fail.
        # TODO(runtime-provisioning): For non-local/staging-hardening, replace
        # sensitive raw env injection with valueFrom.secretKeyRef.

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
        self, *, service_name: str, request: RuntimeProvisionRequest
    ) -> dict[str, object]:
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": {
                "name": service_name,
                "namespace": self._config.namespace,
                "labels": {
                    "app.kubernetes.io/name": "lab-runtime",
                    "agent-failure/session-id": str(request.session_id),
                },
            },
            "spec": {
                "selector": {"agent-failure/session-id": str(request.session_id)},
                "ports": [{"name": "http", "port": 8000, "targetPort": 8000}],
                "type": "ClusterIP",
            },
        }
