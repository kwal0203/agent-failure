from __future__ import annotations

import subprocess
from uuid import uuid4

from apps.control_plane.src.application.orchestrator.types import RuntimeTeardownRequest
from apps.control_plane.src.infrastructure.orchestrator.k8s_teardown import (
    K8sRuntimeTeardown,
)
from apps.control_plane.src.infrastructure.orchestrator.types import K8sCleanupConfig


def _result(
    stdout: str = "", *, returncode: int = 0
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=["kubectl"], returncode=returncode, stdout=stdout, stderr=""
    )


def test_teardown_deletes_and_verifies_all_session_resources(monkeypatch) -> None:
    session_id = uuid4()
    calls: list[list[str]] = []
    get_count = 0

    def _run(args, **kwargs):
        nonlocal get_count
        _ = kwargs
        calls.append(args)
        if "get" in args:
            get_count += 1
            if get_count == 1:
                return _result("pod/session-a\nservice/session-a\n")
            return _result()
        return _result()

    monkeypatch.setattr(subprocess, "run", _run)
    teardown = K8sRuntimeTeardown(
        config=K8sCleanupConfig(namespace="test-runtime", kubectl_bin="kubectl")
    )

    result = teardown.teardown(
        RuntimeTeardownRequest(session_id=session_id, runtime_id="session-a")
    )

    assert result.status == "deleted"
    delete_call = next(call for call in calls if "delete" in call)
    assert "pod,service" in delete_call
    assert f"agent-failure/session-id={session_id}" in delete_call
    assert "--ignore-not-found=true" in delete_call


def test_teardown_fails_when_any_labeled_resource_remains(monkeypatch) -> None:
    session_id = uuid4()
    get_count = 0

    def _run(args, **kwargs):
        nonlocal get_count
        _ = kwargs
        if "get" in args:
            get_count += 1
            return (
                _result("pod/session-a\nservice/session-a\n")
                if get_count == 1
                else _result("service/session-a\n")
            )
        return _result()

    monkeypatch.setattr(subprocess, "run", _run)
    teardown = K8sRuntimeTeardown()

    result = teardown.teardown(
        RuntimeTeardownRequest(session_id=session_id, runtime_id="session-a")
    )

    assert result.status == "failed"
    assert result.reason_code == "K8S_RESOURCES_STILL_EXIST"
    assert result.details == {
        "pod_name": "session-a",
        "remaining_resources": ["service/session-a"],
    }
