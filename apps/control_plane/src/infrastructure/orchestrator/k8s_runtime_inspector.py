from apps.control_plane.src.application.orchestrator.ports import RuntimeInspectorPort
from apps.control_plane.src.application.orchestrator.types import (
    RuntimeInspectorRequest,
    RuntimeInspectorResult,
)
from uuid import UUID
from typing import cast, Any

from .types import K8sRuntimeInspectorConfig

import subprocess
import json


class K8sRuntimeInspector(RuntimeInspectorPort):
    def __init__(self, config: K8sRuntimeInspectorConfig | None = None) -> None:
        self._config = config or K8sRuntimeInspectorConfig()

    def inspect(self, request: RuntimeInspectorRequest) -> RuntimeInspectorResult:
        session_id = request.session_id
        runtime_id = request.runtime_id
        try:
            raw = self._kubectl_get_pods_by_session(session_id=session_id)
            items_raw_obj = raw.get("items", [])
            if not isinstance(items_raw_obj, list):
                items_raw_obj = []

            items_unknown = cast(list[object], items_raw_obj)
            items: list[dict[str, Any]] = []
            for obj in items_unknown:
                if isinstance(obj, dict):
                    items.append(cast(dict[str, Any], obj))

            pod_names: list[str] = []
            phase: str | None = None
            ready: bool | None = None
            reason: str | None = None

            for item in items:
                metadata_obj = item.get("metadata")
                if isinstance(metadata_obj, dict):
                    metadata = cast(dict[str, Any], metadata_obj)
                    name = metadata.get("name")
                    if isinstance(name, str):
                        pod_names.append(name)

                status_obj = item.get("status")
                if phase is None and isinstance(status_obj, dict):
                    status = cast(dict[str, Any], status_obj)

                    p = status.get("phase")
                    if isinstance(p, str):
                        phase = p

                    r = status.get("reason")
                    if isinstance(r, str):
                        reason = r

                    conditions_obj = status.get("conditions")
                    if isinstance(conditions_obj, list):
                        conditions = cast(list[dict[str, Any]], conditions_obj)
                        for cond in conditions:
                            if cond.get("type") == "Ready":
                                ready = cond.get("status") == "True"
                                break

            matched_runtime_ids = tuple(pod_names)
            exists = len(matched_runtime_ids) > 0
            duplicate_count = max(0, len(matched_runtime_ids) - 1)

            return RuntimeInspectorResult(
                session_id=session_id,
                requested_runtime_id=runtime_id,
                matched_runtime_ids=matched_runtime_ids,
                exists=exists,
                duplicate_count=duplicate_count,
                phase=phase,
                ready=ready,
                reason=reason,
                details=None,
            )
        except subprocess.CalledProcessError as exc:
            return RuntimeInspectorResult(
                session_id=session_id,
                requested_runtime_id=runtime_id,
                matched_runtime_ids=tuple(),
                exists=False,
                duplicate_count=0,
                phase=None,
                ready=None,
                reason="K8S_INSPECT_FAILED",
                details={
                    "returncode": exc.returncode,
                    "stderr": str(exc.stderr),
                    "stdout": str(exc.stdout),
                },
            )
        except json.JSONDecodeError as exc:
            return RuntimeInspectorResult(
                session_id=session_id,
                requested_runtime_id=runtime_id,
                matched_runtime_ids=tuple(),
                exists=False,
                duplicate_count=0,
                phase=None,
                ready=None,
                reason="K8S_INSPECT_BAD_JSON",
                details={"error": str(exc)},
            )

    def _kubectl_get_pods_by_session(self, session_id: UUID) -> dict[str, object]:
        result = subprocess.run(
            [
                self._config.kubectl_bin,
                "-n",
                self._config.namespace,
                "get",
                "pods",
                "-l",
                f"agent-failure/session-id={session_id}",
                "-o",
                "json",
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        return json.loads(result.stdout)
