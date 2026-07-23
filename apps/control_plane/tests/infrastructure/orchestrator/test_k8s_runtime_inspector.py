from typing import cast
from unittest.mock import Mock
from uuid import uuid4

from kubernetes import client
from kubernetes.client.exceptions import ApiException

from apps.control_plane.src.application.orchestrator.types import (
    RuntimeInspectorRequest,
)
from apps.control_plane.src.infrastructure.orchestrator.k8s_runtime_inspector import (
    K8sRuntimeInspector,
)


def _pod(name: str) -> client.V1Pod:
    return client.V1Pod(
        metadata=client.V1ObjectMeta(name=name),
        status=client.V1PodStatus(
            phase="Running",
            conditions=[client.V1PodCondition(type="Ready", status="True")],
        ),
    )


def _api_returning(*pods: client.V1Pod) -> client.CoreV1Api:
    api = Mock(spec=client.CoreV1Api)
    api.list_namespaced_pod.return_value = client.V1PodList(items=list(pods))
    return cast(client.CoreV1Api, api)


def test_inspector_requires_runtime_id_match_when_provided() -> None:
    inspector = K8sRuntimeInspector(core_api=_api_returning(_pod("session-other")))
    session_id = uuid4()

    result = inspector.inspect(
        RuntimeInspectorRequest(session_id=session_id, runtime_id="session-expected")
    )

    assert result.exists is False
    assert result.matched_runtime_ids == ("session-other",)
    assert result.phase == "Running"
    assert result.ready is True


def test_inspector_matches_runtime_id_when_present() -> None:
    inspector = K8sRuntimeInspector(core_api=_api_returning(_pod("session-expected")))
    session_id = uuid4()

    result = inspector.inspect(
        RuntimeInspectorRequest(session_id=session_id, runtime_id="session-expected")
    )

    assert result.exists is True
    assert result.matched_runtime_ids == ("session-expected",)


def test_inspector_reports_structured_kubernetes_api_error() -> None:
    api = Mock(spec=client.CoreV1Api)
    api.list_namespaced_pod.side_effect = ApiException(
        status=503,
        reason="Service Unavailable",
        http_resp=None,
    )
    inspector = K8sRuntimeInspector(core_api=cast(client.CoreV1Api, api))

    result = inspector.inspect(
        RuntimeInspectorRequest(session_id=uuid4(), runtime_id="session-expected")
    )

    assert result.exists is False
    assert result.reason == "K8S_INSPECT_FAILED"
    assert result.details is not None
    assert result.details["status"] == 503
    assert result.details["reason"] == "Service Unavailable"
