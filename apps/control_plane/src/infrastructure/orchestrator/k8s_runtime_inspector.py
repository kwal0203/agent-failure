from typing import cast
from uuid import UUID

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from apps.control_plane.src.application.orchestrator.ports import RuntimeInspectorPort
from apps.control_plane.src.application.orchestrator.types import (
    RuntimeInspectorRequest,
    RuntimeInspectorResult,
)

from .k8s_client import create_core_v1_api
from .types import K8sRuntimeInspectorConfig, SESSION_LABEL


class K8sRuntimeInspector(RuntimeInspectorPort):
    def __init__(
        self,
        config: K8sRuntimeInspectorConfig | None = None,
        core_api: client.CoreV1Api | None = None,
    ) -> None:
        self._config = config or K8sRuntimeInspectorConfig()
        self._configured_core_api = core_api

    @property
    def _core_api(self) -> client.CoreV1Api:
        if self._configured_core_api is None:
            self._configured_core_api = create_core_v1_api()
        return self._configured_core_api

    def inspect(self, request: RuntimeInspectorRequest) -> RuntimeInspectorResult:
        session_id = request.session_id
        runtime_id = request.runtime_id
        try:
            pods = self._get_pods_by_session(session_id=session_id)
            pod_names = tuple(
                pod.metadata.name
                for pod in pods
                if pod.metadata is not None and pod.metadata.name is not None
            )

            phase: str | None = None
            ready: bool | None = None
            reason: str | None = None
            if pods and pods[0].status is not None:
                status = pods[0].status
                phase = status.phase
                reason = status.reason
                for condition in status.conditions or []:
                    if condition.type == "Ready":
                        ready = condition.status == "True"
                        break

            exists = (
                runtime_id in pod_names
                if runtime_id and runtime_id.strip()
                else bool(pod_names)
            )
            return RuntimeInspectorResult(
                session_id=session_id,
                requested_runtime_id=runtime_id,
                matched_runtime_ids=pod_names,
                exists=exists,
                duplicate_count=max(0, len(pod_names) - 1),
                phase=phase,
                ready=ready,
                reason=reason,
                details=None,
            )
        except ApiException as exc:
            return RuntimeInspectorResult(
                session_id=session_id,
                requested_runtime_id=runtime_id,
                matched_runtime_ids=tuple(),
                exists=False,
                duplicate_count=0,
                phase=None,
                ready=None,
                reason="K8S_INSPECT_FAILED",
                details={
                    "status": exc.status,
                    "reason": str(exc.reason or ""),
                    "body": str(exc.body or ""),
                },
            )
        except Exception as exc:
            return RuntimeInspectorResult(
                session_id=session_id,
                requested_runtime_id=runtime_id,
                matched_runtime_ids=tuple(),
                exists=False,
                duplicate_count=0,
                phase=None,
                ready=None,
                reason="K8S_INSPECT_INTERNAL_ERROR",
                details={"error": str(exc)},
            )

    def _get_pods_by_session(self, session_id: UUID) -> list[client.V1Pod]:
        result = cast(
            client.V1PodList,
            self._core_api.list_namespaced_pod(
                namespace=self._config.namespace,
                label_selector=f"{SESSION_LABEL}={session_id}",
                _request_timeout=self._config.api_request_timeout_seconds,
            ),
        )
        return list(result.items or [])
