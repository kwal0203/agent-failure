from __future__ import annotations

import json
import subprocess
from typing import Any
from uuid import uuid4

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


def test_provision_then_teardown_leaves_no_pod_or_service(monkeypatch) -> None:
    resources: dict[tuple[str, str], dict[str, Any]] = {}

    def _completed(
        args: list[str], *, stdout: str = ""
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout=stdout, stderr=""
        )

    def _run(args: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if "apply" in args:
            manifest = json.loads(kwargs["input"])
            kind = str(manifest["kind"]).lower()
            name = str(manifest["metadata"]["name"])
            if kind == "pod":
                manifest["metadata"]["uid"] = "pod-uid-integration"
            resources[(kind, name)] = manifest
            return _completed(args)

        if "get" in args and "jsonpath={.metadata.uid}" in args:
            pod_name = args[args.index("pod") + 1]
            pod = resources[("pod", pod_name)]
            return _completed(args, stdout=str(pod["metadata"]["uid"]))

        if "get" in args and "pod,service" in args:
            selector = args[args.index("-l") + 1]
            label_key, label_value = selector.split("=", maxsplit=1)
            names = [
                f"{kind}/{name}"
                for (kind, name), manifest in resources.items()
                if manifest["metadata"]["labels"].get(label_key) == label_value
            ]
            stdout = "".join(f"{name}\n" for name in sorted(names))
            return _completed(args, stdout=stdout)

        if "delete" in args and "pod,service" in args:
            selector = args[args.index("-l") + 1]
            label_key, label_value = selector.split("=", maxsplit=1)
            for key, manifest in list(resources.items()):
                if manifest["metadata"]["labels"].get(label_key) == label_value:
                    del resources[key]
            return _completed(args)

        raise AssertionError(f"Unexpected kubectl invocation: {args}")

    monkeypatch.setattr(subprocess, "run", _run)
    provisioner = K8sRuntimeProvisioner(
        config=K8sProvisionerConfig(namespace="test-runtime")
    )
    teardown = K8sRuntimeTeardown(config=K8sCleanupConfig(namespace="test-runtime"))
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
    assert {kind for kind, _ in resources} == {"pod", "service"}
    service = next(
        manifest for (kind, _), manifest in resources.items() if kind == "service"
    )
    assert service["metadata"]["ownerReferences"][0]["uid"] == "pod-uid-integration"

    result = teardown.teardown(
        RuntimeTeardownRequest(
            session_id=request.session_id,
            runtime_id=provisioned.runtime_id,
        )
    )

    assert result.status == "deleted"
    assert resources == {}
