import time
from typing import cast

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from apps.control_plane.src.application.orchestrator.ports import RuntimeTeardownPort
from apps.control_plane.src.application.orchestrator.types import (
    RuntimeTeardownRequest,
    RuntimeTeardownResult,
)

from .k8s_client import create_core_v1_api
from .types import K8sCleanupConfig, SESSION_LABEL


class K8sRuntimeTeardown(RuntimeTeardownPort):
    def __init__(
        self,
        config: K8sCleanupConfig | None = None,
        core_api: client.CoreV1Api | None = None,
    ) -> None:
        self._config = config or K8sCleanupConfig()
        self._configured_core_api = core_api

    @property
    def _core_api(self) -> client.CoreV1Api:
        if self._configured_core_api is None:
            self._configured_core_api = create_core_v1_api()
        return self._configured_core_api

    def teardown(self, request: RuntimeTeardownRequest) -> RuntimeTeardownResult:
        session_id = request.session_id
        pod_name = request.runtime_id or f"session-{str(session_id)[:8]}"
        selector = f"{SESSION_LABEL}={session_id}"
        try:
            before = self._resource_names(selector)
            self._delete_resources(selector)
            remaining = self._wait_for_deletion(selector)
            if remaining:
                return RuntimeTeardownResult(
                    status="failed",
                    reason_code="K8S_RESOURCES_STILL_EXIST",
                    details={
                        "pod_name": pod_name,
                        "remaining_resources": remaining,
                    },
                )
            existed = bool(before)
            return RuntimeTeardownResult(
                status="deleted" if existed else "already_gone",
                reason_code=None if existed else "K8S_RESOURCES_NOT_FOUND",
                details={"pod_name": pod_name, "session_id": str(session_id)},
            )
        except ApiException as exc:
            if exc.status == 404:
                return RuntimeTeardownResult(
                    status="already_gone",
                    reason_code="K8S_RESOURCES_NOT_FOUND",
                    details={"pod_name": pod_name},
                )
            return RuntimeTeardownResult(
                status="failed",
                reason_code="K8S_RESOURCE_DELETE_FAILED",
                details={
                    "status": exc.status,
                    "reason": str(exc.reason or ""),
                    "body": str(exc.body or ""),
                },
            )
        except Exception as exc:
            return RuntimeTeardownResult(
                status="failed",
                reason_code="DELETE_INTERNAL_ERROR",
                details={"error": str(exc)},
            )

    def _delete_resources(self, selector: str) -> None:
        # Delete Services explicitly before Pods. The owner reference also lets
        # Kubernetes garbage-collect a Service if provisioning was interrupted.
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

    def _wait_for_deletion(self, selector: str) -> list[str]:
        deadline = time.monotonic() + self._config.deletion_timeout_seconds
        while True:
            remaining = self._resource_names(selector)
            if not remaining or time.monotonic() >= deadline:
                return remaining
            time.sleep(self._config.deletion_poll_interval_seconds)

    def _resource_names(self, selector: str) -> list[str]:
        pods = cast(
            client.V1PodList,
            self._core_api.list_namespaced_pod(
                namespace=self._config.namespace,
                label_selector=selector,
                _request_timeout=self._config.api_request_timeout_seconds,
            ),
        )
        services = cast(
            client.V1ServiceList,
            self._core_api.list_namespaced_service(
                namespace=self._config.namespace,
                label_selector=selector,
                _request_timeout=self._config.api_request_timeout_seconds,
            ),
        )
        names = [
            f"pod/{pod.metadata.name}"
            for pod in pods.items or []
            if pod.metadata is not None and pod.metadata.name is not None
        ]
        names.extend(
            f"service/{service.metadata.name}"
            for service in services.items or []
            if service.metadata is not None and service.metadata.name is not None
        )
        return sorted(names)

    def resources_exist(self, session_id: str) -> bool:
        selector = f"{SESSION_LABEL}={session_id}"
        return bool(self._resource_names(selector))
