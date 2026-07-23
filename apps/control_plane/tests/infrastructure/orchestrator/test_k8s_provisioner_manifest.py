from __future__ import annotations

from typing import Any, cast
from uuid import uuid4

from apps.control_plane.src.application.orchestrator.types import (
    RuntimeProvisionRequest,
)
from apps.control_plane.src.infrastructure.orchestrator.k8s_provisioner import (
    K8sRuntimeProvisioner,
)
from apps.control_plane.src.infrastructure.orchestrator.types import (
    K8sProvisionerConfig,
)


def _as_dict(value: object) -> dict[str, Any]:
    return cast(dict[str, Any], value)


def _as_list(value: object) -> list[Any]:
    return cast(list[Any], value)


def _request() -> RuntimeProvisionRequest:
    return RuntimeProvisionRequest(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        lab_difficulty="medium",
        image_ref="ghcr.io/test/runtime@sha256:abc123",
        metadata={},
    )


def test_build_pod_manifest_applies_security_profile_and_resources() -> None:
    provisioner = K8sRuntimeProvisioner(config=K8sProvisionerConfig())
    request = _request()

    manifest = provisioner._build_pod_manifest(
        pod_name=f"session-{str(request.session_id)[:8]}",
        image_ref=request.image_ref,
        metadata=request.metadata,
        request=request,
    )

    spec = _as_dict(manifest["spec"])
    container = _as_dict(_as_list(spec["containers"])[0])

    assert spec["imagePullSecrets"] == [{"name": "ghcr-pull"}]
    assert spec["automountServiceAccountToken"] is False
    assert spec["securityContext"]["seccompProfile"]["type"] == "RuntimeDefault"

    assert container["securityContext"]["runAsNonRoot"] is True
    assert container["securityContext"]["allowPrivilegeEscalation"] is False
    assert container["securityContext"]["capabilities"]["drop"] == ["ALL"]
    assert container["securityContext"].get("privileged") in (None, False)

    assert container["resources"]["requests"] == {
        "cpu": "250m",
        "memory": "256Mi",
        "ephemeral-storage": "512Mi",
    }
    assert container["resources"]["limits"] == {
        "cpu": "1000m",
        "memory": "1Gi",
        "ephemeral-storage": "1Gi",
    }
    assert {"name": "LAB_DIFFICULTY", "value": "medium"} in container["env"]
    env_by_name = {item["name"]: item for item in container["env"]}
    assert env_by_name["RUNTIME_SHARED_TOKEN"] == {
        "name": "RUNTIME_SHARED_TOKEN",
        "valueFrom": {
            "secretKeyRef": {
                "name": "runtime-secrets",
                "key": "RUNTIME_SHARED_TOKEN",
                "optional": False,
            }
        },
    }
    assert env_by_name["OPENROUTER_API_KEY"] == {
        "name": "OPENROUTER_API_KEY",
        "valueFrom": {
            "secretKeyRef": {
                "name": "runtime-secrets",
                "key": "OPENROUTER_API_KEY",
                "optional": False,
            }
        },
    }
    assert "value" not in env_by_name["RUNTIME_SHARED_TOKEN"]
    assert "value" not in env_by_name["OPENROUTER_API_KEY"]

    for volume in _as_list(spec.get("volumes", [])):
        assert "hostPath" not in volume


def test_pod_and_service_share_labels_and_service_is_owned_by_pod() -> None:
    provisioner = K8sRuntimeProvisioner(config=K8sProvisionerConfig())
    request = _request()
    pod_name = f"session-{str(request.session_id)[:8]}"

    pod = provisioner._build_pod_manifest(
        pod_name=pod_name,
        image_ref=request.image_ref,
        metadata=request.metadata,
        request=request,
    )
    service = provisioner._build_service_manifest(
        service_name=pod_name,
        pod_name=pod_name,
        pod_uid="pod-uid-123",
        request=request,
    )

    pod_metadata = _as_dict(pod["metadata"])
    service_metadata = _as_dict(service["metadata"])
    service_spec = _as_dict(service["spec"])
    assert pod_metadata["labels"] == service_metadata["labels"]
    assert service_spec["selector"] == {
        "agent-failure/session-id": str(request.session_id)
    }
    assert service_metadata["ownerReferences"] == [
        {
            "apiVersion": "v1",
            "kind": "Pod",
            "name": pod_name,
            "uid": "pod-uid-123",
            "controller": True,
            "blockOwnerDeletion": False,
        }
    ]


def test_build_pod_manifest_adds_tmp_mount_only_when_read_only_rootfs_enabled() -> None:
    with_rootfs_read_only = K8sRuntimeProvisioner(
        config=K8sProvisionerConfig(read_only_root_filesystem=True)
    )
    request = _request()
    manifest_read_only = with_rootfs_read_only._build_pod_manifest(
        pod_name=f"session-{str(request.session_id)[:8]}",
        image_ref=request.image_ref,
        metadata=request.metadata,
        request=request,
    )

    spec_read_only = _as_dict(manifest_read_only["spec"])
    container_read_only = _as_dict(_as_list(spec_read_only["containers"])[0])
    assert spec_read_only["volumes"] == [{"name": "tmp", "emptyDir": {}}]
    assert container_read_only["volumeMounts"] == [{"name": "tmp", "mountPath": "/tmp"}]

    with_rootfs_writable = K8sRuntimeProvisioner(
        config=K8sProvisionerConfig(read_only_root_filesystem=False)
    )
    manifest_writable = with_rootfs_writable._build_pod_manifest(
        pod_name=f"session-{str(request.session_id)[:8]}",
        image_ref=request.image_ref,
        metadata=request.metadata,
        request=request,
    )

    spec_writable = _as_dict(manifest_writable["spec"])
    container_writable = _as_dict(_as_list(spec_writable["containers"])[0])
    assert "volumes" not in spec_writable
    assert "volumeMounts" not in container_writable
