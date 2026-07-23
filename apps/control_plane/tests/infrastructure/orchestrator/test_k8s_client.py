from unittest.mock import Mock

import pytest
from kubernetes import client
from kubernetes.config.config_exception import ConfigException

from apps.control_plane.src.infrastructure.orchestrator import k8s_client


def test_client_uses_incluster_credentials_inside_kubernetes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "kubernetes.default.svc")
    load_incluster = Mock()
    load_kubeconfig = Mock()
    expected = Mock(spec=client.CoreV1Api)
    monkeypatch.setattr(k8s_client.config, "load_incluster_config", load_incluster)
    monkeypatch.setattr(k8s_client.config, "load_kube_config", load_kubeconfig)
    monkeypatch.setattr(k8s_client.client, "CoreV1Api", Mock(return_value=expected))

    result = k8s_client.create_core_v1_api()

    assert result is expected
    load_incluster.assert_called_once_with()
    load_kubeconfig.assert_not_called()


def test_client_uses_kubeconfig_outside_kubernetes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
    load_incluster = Mock()
    load_kubeconfig = Mock()
    monkeypatch.setattr(k8s_client.config, "load_incluster_config", load_incluster)
    monkeypatch.setattr(k8s_client.config, "load_kube_config", load_kubeconfig)

    k8s_client.create_core_v1_api()

    load_incluster.assert_not_called()
    load_kubeconfig.assert_called_once_with()


def test_client_fails_closed_when_credentials_are_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
    monkeypatch.setattr(
        k8s_client.config,
        "load_kube_config",
        Mock(side_effect=ConfigException("missing kubeconfig")),
    )

    with pytest.raises(
        RuntimeError,
        match="Unable to configure Kubernetes client from local kubeconfig",
    ):
        k8s_client.create_core_v1_api()
