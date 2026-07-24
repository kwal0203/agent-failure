from __future__ import annotations

import os

from kubernetes import client, config
from kubernetes.config.config_exception import ConfigException


def create_core_v1_api() -> client.CoreV1Api:
    """Create an authenticated Core API client for a worker or local operator."""
    try:
        if os.getenv("KUBERNETES_SERVICE_HOST"):
            config.load_incluster_config()
        else:
            config.load_kube_config()
    except ConfigException as exc:
        location = (
            "in-cluster service account"
            if os.getenv("KUBERNETES_SERVICE_HOST")
            else "local kubeconfig"
        )
        raise RuntimeError(
            f"Unable to configure Kubernetes client from {location}"
        ) from exc

    return client.CoreV1Api()
