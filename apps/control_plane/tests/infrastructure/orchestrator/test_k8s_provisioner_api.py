from typing import cast
from unittest.mock import Mock
from uuid import uuid4

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from apps.control_plane.src.application.orchestrator.types import (
    RuntimeProvisionRequest,
)
from apps.control_plane.src.infrastructure.orchestrator.k8s_provisioner import (
    SERVER_SIDE_APPLY_CONTENT_TYPE,
    K8sRuntimeProvisioner,
)
from apps.control_plane.src.infrastructure.orchestrator.types import (
    K8sProvisionerConfig,
)


def _request() -> RuntimeProvisionRequest:
    return RuntimeProvisionRequest(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        lab_difficulty="medium",
        image_ref="ghcr.io/test/runtime@sha256:abc123",
        metadata={},
    )


def test_provision_uses_strict_server_side_apply() -> None:
    request = _request()
    pod_name = f"session-{str(request.session_id)[:8]}"
    api_mock = Mock(spec=client.CoreV1Api)
    api_mock.patch_namespaced_pod.return_value = client.V1Pod(
        metadata=client.V1ObjectMeta(name=pod_name, uid="pod-uid-123")
    )
    api_mock.patch_namespaced_service.return_value = client.V1Service()
    provisioner = K8sRuntimeProvisioner(
        config=K8sProvisionerConfig(namespace="test-runtime"),
        core_api=cast(client.CoreV1Api, api_mock),
    )

    result = provisioner.provision(request)

    assert result.status == "accepted"
    pod_call = api_mock.patch_namespaced_pod.call_args
    assert pod_call.kwargs["name"] == pod_name
    assert pod_call.kwargs["namespace"] == "test-runtime"
    assert isinstance(pod_call.kwargs["body"], client.V1Pod)
    assert pod_call.kwargs["field_manager"] == "agent-failure-control-plane"
    assert pod_call.kwargs["force"] is True
    assert pod_call.kwargs["field_validation"] == "Strict"
    assert pod_call.kwargs["_content_type"] == SERVER_SIDE_APPLY_CONTENT_TYPE

    service_call = api_mock.patch_namespaced_service.call_args
    assert service_call.kwargs["name"] == pod_name
    assert isinstance(service_call.kwargs["body"], client.V1Service)
    assert service_call.kwargs["_content_type"] == SERVER_SIDE_APPLY_CONTENT_TYPE


def test_partial_provisioning_failure_cleans_up_pod_and_service_by_label() -> None:
    request = _request()
    selector = f"agent-failure/session-id={request.session_id}"
    api_mock = Mock(spec=client.CoreV1Api)
    api_mock.patch_namespaced_pod.return_value = client.V1Pod(
        metadata=client.V1ObjectMeta(uid="pod-uid-123")
    )
    api_mock.patch_namespaced_service.side_effect = ApiException(
        status=422,
        reason="Invalid",
        http_resp=None,
    )
    provisioner = K8sRuntimeProvisioner(core_api=cast(client.CoreV1Api, api_mock))

    result = provisioner.provision(request)

    assert result.status == "failed"
    assert result.reason_code == "K8S_APPLY_FAILED"
    api_mock.delete_collection_namespaced_service.assert_called_once_with(
        namespace="runtime-pool",
        label_selector=selector,
        propagation_policy="Foreground",
        _request_timeout=30.0,
    )
    api_mock.delete_collection_namespaced_pod.assert_called_once_with(
        namespace="runtime-pool",
        label_selector=selector,
        propagation_policy="Foreground",
        _request_timeout=30.0,
    )
