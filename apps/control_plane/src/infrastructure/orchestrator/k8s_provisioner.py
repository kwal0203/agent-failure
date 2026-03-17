from apps.orchestrator.ports import RuntimeProvisionerPort
from apps.orchestrator.types import ProvisionResult, RuntimeProvisionRequest
from typing import Mapping

from .types import K8sProvisionerConfig

import subprocess
import json


class K8sRuntimeProvisioner(RuntimeProvisionerPort):
    def __init__(self, config: K8sProvisionerConfig | None = None) -> None:
        self._config = config or K8sProvisionerConfig()

    def provision(self, request: RuntimeProvisionRequest) -> ProvisionResult:
        pod_name = f"session-{str(request.session_id)[:8]}"

        manifest = self._build_pod_manifest(
            pod_name=pod_name,
            image_ref=request.image_ref,
            metadata=request.metadata,
            request=request,
        )

        try:
            self._kubectl_apply(manifest)
            return ProvisionResult(
                status="accepted",
                runtime_id=pod_name,
                details={"namespace": self._config.namespace},
            )
        except subprocess.CalledProcessError as exc:
            return ProvisionResult(
                status="failed",
                reason_code="K8S_APPLY_FAILED",
                details={
                    "returncode": exc.returncode,
                    "stderr": exc.stderr.decode("utf-8", errors="replace")
                    if isinstance(exc.stderr, (bytes, bytearray))
                    else str(exc.stderr),
                },
            )
        except Exception as exc:
            return ProvisionResult(
                status="failed",
                reason_code="PROVISION_INTERNAL_ERROR",
                details={"error": str(exc)},
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

        return {
            "apiVersion": "v1",
            "kind": "Pod",
            "metadata": {
                "name": pod_name,
                "namespace": self._config.namespace,
                "labels": labels,
            },
            "spec": {
                "restartPolicy": "Never",
                "containers": [
                    {
                        "name": "runtime",
                        "image": image_ref,
                        "imagePullPolicy": "IfNotPresent",
                    }
                ],
            },
        }
