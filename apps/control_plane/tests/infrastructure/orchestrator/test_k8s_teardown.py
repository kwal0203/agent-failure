from typing import cast
from unittest.mock import Mock, call
from uuid import uuid4

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from apps.control_plane.src.application.orchestrator.types import RuntimeTeardownRequest
from apps.control_plane.src.infrastructure.orchestrator.k8s_teardown import (
    K8sRuntimeTeardown,
)
from apps.control_plane.src.infrastructure.orchestrator.types import K8sCleanupConfig


def _pod_list(*names: str) -> client.V1PodList:
    return client.V1PodList(
        items=[client.V1Pod(metadata=client.V1ObjectMeta(name=name)) for name in names]
    )


def _service_list(*names: str) -> client.V1ServiceList:
    return client.V1ServiceList(
        items=[
            client.V1Service(metadata=client.V1ObjectMeta(name=name)) for name in names
        ]
    )


def test_teardown_deletes_and_verifies_all_session_resources() -> None:
    session_id = uuid4()
    selector = f"agent-failure/session-id={session_id}"
    api_mock = Mock(spec=client.CoreV1Api)
    api_mock.list_namespaced_pod.side_effect = [
        _pod_list("session-a"),
        _pod_list(),
    ]
    api_mock.list_namespaced_service.side_effect = [
        _service_list("session-a"),
        _service_list(),
    ]
    teardown = K8sRuntimeTeardown(
        config=K8sCleanupConfig(namespace="test-runtime"),
        core_api=cast(client.CoreV1Api, api_mock),
    )

    result = teardown.teardown(
        RuntimeTeardownRequest(session_id=session_id, runtime_id="session-a")
    )

    assert result.status == "deleted"
    api_mock.delete_collection_namespaced_service.assert_called_once_with(
        namespace="test-runtime",
        label_selector=selector,
        propagation_policy="Foreground",
        _request_timeout=30.0,
    )
    api_mock.delete_collection_namespaced_pod.assert_called_once_with(
        namespace="test-runtime",
        label_selector=selector,
        propagation_policy="Foreground",
        _request_timeout=30.0,
    )
    assert api_mock.method_calls.index(
        call.delete_collection_namespaced_service(
            namespace="test-runtime",
            label_selector=selector,
            propagation_policy="Foreground",
            _request_timeout=30.0,
        )
    ) < api_mock.method_calls.index(
        call.delete_collection_namespaced_pod(
            namespace="test-runtime",
            label_selector=selector,
            propagation_policy="Foreground",
            _request_timeout=30.0,
        )
    )


def test_teardown_fails_when_any_labeled_resource_remains() -> None:
    session_id = uuid4()
    api_mock = Mock(spec=client.CoreV1Api)
    api_mock.list_namespaced_pod.side_effect = [
        _pod_list("session-a"),
        _pod_list(),
    ]
    api_mock.list_namespaced_service.side_effect = [
        _service_list("session-a"),
        _service_list("session-a"),
    ]
    teardown = K8sRuntimeTeardown(
        config=K8sCleanupConfig(deletion_timeout_seconds=0),
        core_api=cast(client.CoreV1Api, api_mock),
    )

    result = teardown.teardown(
        RuntimeTeardownRequest(session_id=session_id, runtime_id="session-a")
    )

    assert result.status == "failed"
    assert result.reason_code == "K8S_RESOURCES_STILL_EXIST"
    assert result.details == {
        "pod_name": "session-a",
        "remaining_resources": ["service/session-a"],
    }


def test_teardown_polls_until_async_deletion_finishes() -> None:
    session_id = uuid4()
    api_mock = Mock(spec=client.CoreV1Api)
    api_mock.list_namespaced_pod.side_effect = [
        _pod_list("session-a"),
        _pod_list("session-a"),
        _pod_list(),
    ]
    api_mock.list_namespaced_service.side_effect = [
        _service_list("session-a"),
        _service_list(),
        _service_list(),
    ]
    teardown = K8sRuntimeTeardown(
        config=K8sCleanupConfig(deletion_poll_interval_seconds=0),
        core_api=cast(client.CoreV1Api, api_mock),
    )

    result = teardown.teardown(
        RuntimeTeardownRequest(session_id=session_id, runtime_id="session-a")
    )

    assert result.status == "deleted"
    assert api_mock.list_namespaced_pod.call_count == 3
    assert api_mock.list_namespaced_service.call_count == 3


def test_teardown_reports_structured_kubernetes_api_error() -> None:
    session_id = uuid4()
    api_mock = Mock(spec=client.CoreV1Api)
    api_mock.list_namespaced_pod.side_effect = ApiException(
        status=403,
        reason="Forbidden",
        http_resp=None,
    )
    teardown = K8sRuntimeTeardown(core_api=cast(client.CoreV1Api, api_mock))

    result = teardown.teardown(
        RuntimeTeardownRequest(session_id=session_id, runtime_id="session-a")
    )

    assert result.status == "failed"
    assert result.reason_code == "K8S_RESOURCE_DELETE_FAILED"
    assert result.details is not None
    assert result.details["status"] == 403
    assert result.details["reason"] == "Forbidden"
