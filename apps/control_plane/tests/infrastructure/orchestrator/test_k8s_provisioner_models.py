from __future__ import annotations

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


def _request() -> RuntimeProvisionRequest:
    return RuntimeProvisionRequest(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        image_ref="ghcr.io/test/runtime@sha256:abc123",
        metadata={},
    )


def test_build_pod_applies_security_profile_and_resources() -> None:
    provisioner = K8sRuntimeProvisioner(config=K8sProvisionerConfig())
    request = _request()

    pod = provisioner._build_pod(
        pod_name=f"session-{str(request.session_id)[:8]}",
        image_ref=request.image_ref,
        metadata=request.metadata,
        request=request,
    )

    assert pod.spec is not None
    assert pod.spec.image_pull_secrets[0].name == "ghcr-pull"
    assert pod.spec.automount_service_account_token is False
    assert pod.spec.security_context.seccomp_profile.type == "RuntimeDefault"

    container = pod.spec.containers[0]
    security = container.security_context
    assert security.run_as_non_root is True
    assert security.allow_privilege_escalation is False
    assert security.capabilities.drop == ["ALL"]
    assert security.privileged in (None, False)

    assert container.resources.requests == {
        "cpu": "250m",
        "memory": "256Mi",
        "ephemeral-storage": "512Mi",
    }
    assert container.resources.limits == {
        "cpu": "1000m",
        "memory": "1Gi",
        "ephemeral-storage": "1Gi",
    }
    env_by_name = {item.name: item for item in container.env}
    assert "LAB_DIFFICULTY" not in env_by_name
    assert env_by_name["RUNTIME_SESSION_ID"].value == str(request.session_id)

    shared_token_ref = env_by_name["RUNTIME_SHARED_TOKEN"].value_from.secret_key_ref
    assert shared_token_ref.name == "runtime-secrets"
    assert shared_token_ref.key == "RUNTIME_SHARED_TOKEN"
    assert shared_token_ref.optional is False
    assert env_by_name["RUNTIME_SHARED_TOKEN"].value is None

    openrouter_ref = env_by_name["OPENROUTER_API_KEY"].value_from.secret_key_ref
    assert openrouter_ref.name == "runtime-secrets"
    assert openrouter_ref.key == "OPENROUTER_API_KEY"
    assert openrouter_ref.optional is False
    assert env_by_name["OPENROUTER_API_KEY"].value is None

    assert all(volume.host_path is None for volume in pod.spec.volumes)


def test_pod_and_service_share_labels_and_service_is_owned_by_pod() -> None:
    provisioner = K8sRuntimeProvisioner(config=K8sProvisionerConfig())
    request = _request()
    pod_name = f"session-{str(request.session_id)[:8]}"

    pod = provisioner._build_pod(
        pod_name=pod_name,
        image_ref=request.image_ref,
        metadata=request.metadata,
        request=request,
    )
    service = provisioner._build_service(
        service_name=pod_name,
        pod_name=pod_name,
        pod_uid="pod-uid-123",
        request=request,
    )

    assert pod.metadata is not None
    assert service.metadata is not None
    assert service.spec is not None
    assert pod.metadata.labels == service.metadata.labels
    assert service.spec.selector == {
        "agent-failure/session-id": str(request.session_id)
    }
    owner = service.metadata.owner_references[0]
    assert owner.api_version == "v1"
    assert owner.kind == "Pod"
    assert owner.name == pod_name
    assert owner.uid == "pod-uid-123"
    assert owner.controller is True
    assert owner.block_owner_deletion is False


def test_build_pod_adds_tmp_mount_only_when_read_only_rootfs_enabled() -> None:
    request = _request()
    with_rootfs_read_only = K8sRuntimeProvisioner(
        config=K8sProvisionerConfig(read_only_root_filesystem=True)
    )
    read_only_pod = with_rootfs_read_only._build_pod(
        pod_name=f"session-{str(request.session_id)[:8]}",
        image_ref=request.image_ref,
        metadata=request.metadata,
        request=request,
    )

    assert read_only_pod.spec is not None
    assert read_only_pod.spec.volumes[0].name == "tmp"
    assert read_only_pod.spec.volumes[0].empty_dir is not None
    assert read_only_pod.spec.containers[0].volume_mounts[0].name == "tmp"
    assert read_only_pod.spec.containers[0].volume_mounts[0].mount_path == "/tmp"

    with_rootfs_writable = K8sRuntimeProvisioner(
        config=K8sProvisionerConfig(read_only_root_filesystem=False)
    )
    writable_pod = with_rootfs_writable._build_pod(
        pod_name=f"session-{str(request.session_id)[:8]}",
        image_ref=request.image_ref,
        metadata=request.metadata,
        request=request,
    )

    assert writable_pod.spec is not None
    assert writable_pod.spec.volumes is None
    assert writable_pod.spec.containers[0].volume_mounts is None
