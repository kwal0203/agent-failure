from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

from kubernetes import client

from apps.control_plane.src.application.orchestrator.types import (
    RuntimeProvisionRequest,
    RuntimeTeardownRequest,
)
from apps.control_plane.src.infrastructure.orchestrator.k8s_provisioner import (
    K8sRuntimeProvisioner,
)
from apps.control_plane.src.infrastructure.orchestrator.k8s_teardown import (
    K8sRuntimeTeardown,
)
from apps.control_plane.src.infrastructure.orchestrator.types import (
    K8sCleanupConfig,
    K8sProvisionerConfig,
)


class _InMemoryCoreApi:
    def __init__(self) -> None:
        self.pods: dict[str, client.V1Pod] = {}
        self.services: dict[str, client.V1Service] = {}

    def patch_namespaced_pod(
        self, name: str, namespace: str, body: client.V1Pod, **kwargs: Any
    ) -> client.V1Pod:
        _ = namespace, kwargs
        assert body.metadata is not None
        body.metadata.uid = "pod-uid-integration"
        self.pods[name] = body
        return body

    def patch_namespaced_service(
        self, name: str, namespace: str, body: client.V1Service, **kwargs: Any
    ) -> client.V1Service:
        _ = namespace, kwargs
        self.services[name] = body
        return body

    def list_namespaced_pod(self, namespace: str, **kwargs: Any) -> client.V1PodList:
        _ = namespace
        return client.V1PodList(
            items=[
                pod
                for pod in self.pods.values()
                if pod.metadata is not None
                and _matches_selector(pod.metadata.labels, kwargs["label_selector"])
            ]
        )

    def list_namespaced_service(
        self, namespace: str, **kwargs: Any
    ) -> client.V1ServiceList:
        _ = namespace
        return client.V1ServiceList(
            items=[
                service
                for service in self.services.values()
                if service.metadata is not None
                and _matches_selector(service.metadata.labels, kwargs["label_selector"])
            ]
        )

    def delete_collection_namespaced_pod(self, namespace: str, **kwargs: Any) -> None:
        _ = namespace
        self.pods = {
            name: pod
            for name, pod in self.pods.items()
            if pod.metadata is not None
            and not _matches_selector(pod.metadata.labels, kwargs["label_selector"])
        }

    def delete_collection_namespaced_service(
        self, namespace: str, **kwargs: Any
    ) -> None:
        _ = namespace
        self.services = {
            name: service
            for name, service in self.services.items()
            if service.metadata is not None
            and not _matches_selector(service.metadata.labels, kwargs["label_selector"])
        }


def _matches_selector(labels: dict[str, str], selector: str) -> bool:
    key, value = selector.split("=", maxsplit=1)
    return labels.get(key) == value


def test_provision_then_teardown_leaves_no_pod_or_service() -> None:
    api = _InMemoryCoreApi()
    typed_api = cast(client.CoreV1Api, api)
    provisioner = K8sRuntimeProvisioner(
        config=K8sProvisionerConfig(namespace="test-runtime"),
        core_api=typed_api,
    )
    teardown = K8sRuntimeTeardown(
        config=K8sCleanupConfig(namespace="test-runtime"),
        core_api=typed_api,
    )
    request = RuntimeProvisionRequest(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        lab_difficulty="medium",
        image_ref="ghcr.io/test/runtime@sha256:abc123",
        metadata={},
    )

    provisioned = provisioner.provision(request)

    assert provisioned.status == "accepted"
    assert len(api.pods) == 1
    assert len(api.services) == 1
    service = next(iter(api.services.values()))
    assert service.metadata is not None
    assert service.metadata.owner_references[0].uid == "pod-uid-integration"

    result = teardown.teardown(
        RuntimeTeardownRequest(
            session_id=request.session_id,
            runtime_id=provisioned.runtime_id,
        )
    )

    assert result.status == "deleted"
    assert api.pods == {}
    assert api.services == {}
