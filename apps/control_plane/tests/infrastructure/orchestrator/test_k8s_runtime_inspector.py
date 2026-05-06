from uuid import uuid4

from apps.control_plane.src.application.orchestrator.types import (
    RuntimeInspectorRequest,
)
from apps.control_plane.src.infrastructure.orchestrator.k8s_runtime_inspector import (
    K8sRuntimeInspector,
)


def test_inspector_requires_runtime_id_match_when_provided() -> None:
    inspector = K8sRuntimeInspector()
    session_id = uuid4()

    inspector._kubectl_get_pods_by_session = lambda session_id: {  # type: ignore[method-assign]
        "items": [
            {
                "metadata": {"name": "session-other"},
                "status": {
                    "phase": "Running",
                    "conditions": [{"type": "Ready", "status": "True"}],
                },
            }
        ]
    }

    result = inspector.inspect(
        RuntimeInspectorRequest(session_id=session_id, runtime_id="session-expected")
    )

    assert result.exists is False
    assert result.matched_runtime_ids == ("session-other",)


def test_inspector_matches_runtime_id_when_present() -> None:
    inspector = K8sRuntimeInspector()
    session_id = uuid4()

    inspector._kubectl_get_pods_by_session = lambda session_id: {  # type: ignore[method-assign]
        "items": [
            {
                "metadata": {"name": "session-expected"},
                "status": {
                    "phase": "Running",
                    "conditions": [{"type": "Ready", "status": "True"}],
                },
            }
        ]
    }

    result = inspector.inspect(
        RuntimeInspectorRequest(session_id=session_id, runtime_id="session-expected")
    )

    assert result.exists is True
    assert result.matched_runtime_ids == ("session-expected",)
