import subprocess

from apps.control_plane.src.application.orchestrator.ports import RuntimeTeardownPort
from apps.control_plane.src.application.orchestrator.types import (
    RuntimeTeardownRequest,
    RuntimeTeardownResult,
)

from .types import K8sCleanupConfig, SESSION_LABEL


class K8sRuntimeTeardown(RuntimeTeardownPort):
    def __init__(self, config: K8sCleanupConfig | None = None) -> None:
        self._config = config or K8sCleanupConfig()

    def teardown(self, request: RuntimeTeardownRequest) -> RuntimeTeardownResult:
        session_id = request.session_id
        pod_name = (
            request.runtime_id
            if request.runtime_id
            else f"session-{str(session_id)[:8]}"
        )
        try:
            before = self._kubectl_get_resources(session_id=str(session_id))
            self._kubectl_delete(session_id=str(session_id))
            verify = self._kubectl_get_resources(session_id=str(session_id))
            remaining = self._resource_names(verify)
            if verify.returncode != 0:
                return RuntimeTeardownResult(
                    status="failed",
                    reason_code="K8S_RESOURCE_DELETE_VERIFICATION_FAILED",
                    details={
                        "pod_name": pod_name,
                        "stdout": str(verify.stdout or ""),
                        "stderr": str(verify.stderr or ""),
                    },
                )
            if remaining:
                return RuntimeTeardownResult(
                    status="failed",
                    reason_code="K8S_RESOURCES_STILL_EXIST",
                    details={
                        "pod_name": pod_name,
                        "remaining_resources": remaining,
                    },
                )
            existed = (
                bool(self._resource_names(before)) if before.returncode == 0 else True
            )
            return RuntimeTeardownResult(
                status="deleted" if existed else "already_gone",
                reason_code=None if existed else "K8S_RESOURCES_NOT_FOUND",
                details={"pod_name": pod_name, "session_id": str(session_id)},
            )
        except subprocess.CalledProcessError as exc:
            stderr_text = str(exc.stderr or "")
            stdout_text = str(exc.stdout or "")
            combined = f"{stdout_text}\n{stderr_text}".lower()
            if "notfound" in combined or "not found" in combined:
                return RuntimeTeardownResult(
                    status="already_gone",
                    reason_code="K8S_RESOURCES_NOT_FOUND",
                    details={"pod_name": pod_name},
                )
            return RuntimeTeardownResult(
                status="failed",
                reason_code="K8S_RESOURCE_DELETE_FAILED",
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

    def _kubectl_delete(self, session_id: str) -> None:
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
            check=True,
            capture_output=True,
            text=True,
        )

    def _kubectl_get_resources(
        self, session_id: str
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                self._config.kubectl_bin,
                "-n",
                self._config.namespace,
                "get",
                "pod,service",
                "-l",
                f"{SESSION_LABEL}={session_id}",
                "-o",
                "name",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    @staticmethod
    def _resource_names(result: subprocess.CompletedProcess[str]) -> list[str]:
        return [
            line.strip() for line in (result.stdout or "").splitlines() if line.strip()
        ]

    def resources_exist(self, session_id: str) -> bool:
        result = self._kubectl_get_resources(session_id=session_id)
        if result.returncode != 0:
            raise RuntimeError(result.stderr or "kubectl resource verification failed")
        return bool(self._resource_names(result))
