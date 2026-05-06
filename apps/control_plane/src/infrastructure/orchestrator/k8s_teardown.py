from apps.control_plane.src.application.orchestrator.ports import RuntimeTeardownPort
from apps.control_plane.src.application.orchestrator.types import (
    RuntimeTeardownRequest,
    RuntimeTeardownResult,
)

from .types import K8sCleanupConfig

import subprocess


class K8sRuntimeTeardown(RuntimeTeardownPort):
    def __init__(self, config: K8sCleanupConfig | None = None) -> None:
        self._config = config or K8sCleanupConfig()

    def teardown(self, request: RuntimeTeardownRequest) -> RuntimeTeardownResult:
        session_id = request.session_id
        runtime_id = request.runtime_id
        pod_name = runtime_id if runtime_id else f"session-{str(session_id)[:8]}"
        try:
            self._kubectl_delete(pod_name=pod_name)
            verify = self._kubectl_get_pod(pod_name=pod_name)
            if verify.returncode == 0:
                return RuntimeTeardownResult(
                    status="failed",
                    reason_code="K8S_DELETE_VERIFICATION_FAILED",
                    details={
                        "pod_name": pod_name,
                        "stdout": str(verify.stdout or ""),
                        "stderr": str(verify.stderr or ""),
                    },
                )
            verify_combined = f"{verify.stdout or ''}\n{verify.stderr or ''}".lower()
            if "notfound" in verify_combined or "not found" in verify_combined:
                return RuntimeTeardownResult(
                    status="deleted",
                    reason_code=None,
                    details={"pod_name": pod_name},
                )
            return RuntimeTeardownResult(
                status="failed",
                reason_code="K8S_DELETE_VERIFICATION_UNKNOWN",
                details={
                    "pod_name": pod_name,
                    "stdout": str(verify.stdout or ""),
                    "stderr": str(verify.stderr or ""),
                },
            )
        except subprocess.CalledProcessError as exc:
            stderr_text = str(exc.stderr or "")
            stdout_text = str(exc.stdout or "")
            combined = f"{stdout_text}\n{stderr_text}".lower()
            if "notfound" in combined or "not found" in combined:
                return RuntimeTeardownResult(
                    status="already_gone",
                    reason_code="K8S_POD_NOT_FOUND",
                    details={"pod_name": pod_name},
                )
            return RuntimeTeardownResult(
                status="failed",
                reason_code="K8S_DELETE_FAILED",
                details={
                    "returncode": exc.returncode,
                    "stderr": stderr_text,
                },
            )
        except Exception as exc:
            return RuntimeTeardownResult(
                status="failed",
                reason_code="DELETE_INTERNAL_ERROR",
                details={"error": str(exc)},
            )

    def _kubectl_delete(self, pod_name: str) -> None:
        subprocess.run(
            [
                self._config.kubectl_bin,
                "-n",
                self._config.namespace,
                "delete",
                "pod",
                pod_name,
                "--wait=true",
                "--timeout=30s",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    def _kubectl_get_pod(self, pod_name: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                self._config.kubectl_bin,
                "-n",
                self._config.namespace,
                "get",
                "pod",
                pod_name,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def pod_exists(self, pod_name: str) -> bool:
        result = self._kubectl_get_pod(pod_name=pod_name)
        return result.returncode == 0
