from datetime import timedelta

from .ports import TraceEventPort
from .types import TraceEvent, TraceFamily
from .errors import (
    UnknownTraceFamilyError,
    UnknownTraceEventTypeError,
    MissingTraceContextError,
    TraceValidationError,
)


ALLOWED_EVENT_TYPES: dict[TraceFamily, set[str]] = {
    "lifecycle": {"SESSION_CREATED", "SESSION_TRANSITIONED"},
    "learner": {"USER_PROMPT_SUBMITTED"},
    "runtime": {
        "RUNTIME_PROVISION_REQUESTED",
        "RUNTIME_PROVISION_ACCEPTED",
        "RUNTIME_PROVISION_FAILED",
        "RUNTIME_HEALTH_STATUS",
    },
    "tool": {"TOOL_CALL_REQUESTED", "TOOL_CALL_SUCCEEDED", "TOOL_CALL_FAILED"},
    "model": {
        "MODEL_TURN_STARTED",
        "MODEL_CHUNK_EMITTED",
        "MODEL_TURN_COMPLETED",
        "MODEL_TURN_FAILED",
    },
}

REQUIRED_PAYLOAD_FIELDS: dict[tuple[TraceFamily, str], set[str]] = {
    ("runtime", "RUNTIME_PROVISION_FAILED"): {"reason_code"},
    ("tool", "TOOL_CALL_FAILED"): {"tool_name", "error_code"},
    ("model", "MODEL_TURN_FAILED"): {"provider", "error_code"},
    # ("lifecycle", "SESSION_CREATED"): set(),
    # ("lifecycle", "SESSION_TRANSITIONED"): set(),
    # ("learner", "USER_PROMPT_SUBMITTED"): set(),
    # ("runtime", "RUNTIME_PROVISION_REQUESTED"): set(),
    # ("runtime", "RUNTIME_PROVISION_ACCEPTED"): set(),
    # ("runtime", "RUNTIME_HEALTH_STATUS"): set(),
    # ("tool", "TOOL_CALL_REQUESTED"): set(),
    # ("tool", "TOOL_CALL_SUCCEEDED"): set(),
    # ("model", "MODEL_TURN_STARTED"): set(),
    # ("model", "MODEL_CHUNK_EMITTED"): set(),
    # ("model", "MODEL_TURN_COMPLETED"): set(),
}


def append_trace_event(trace: TraceEvent, repo: TraceEventPort) -> None:

    if trace.family not in ALLOWED_EVENT_TYPES:
        raise UnknownTraceFamilyError(
            family=trace.family,
            details={
                "family": trace.family,
                "event_type": trace.event_type,
                "session_id": str(trace.session_id),
                "source": trace.source,
                "trace_version": trace.trace_version,
                "allowed_families": sorted(ALLOWED_EVENT_TYPES),
            },
        )

    if trace.event_type not in ALLOWED_EVENT_TYPES[trace.family]:
        raise UnknownTraceEventTypeError(
            family=trace.family,
            event_type=trace.event_type,
            details={
                "family": trace.family,
                "event_type": trace.event_type,
                "session_id": str(trace.session_id),
                "source": trace.source,
                "trace_version": trace.trace_version,
                "allowed_event_types": sorted(ALLOWED_EVENT_TYPES[trace.family]),
            },
        )

    # NOTE(P1-E6-T4): Context validation is intentionally minimal for now.
    # We currently enforce only learner actor attribution; T4 should extend this
    # to per-event requirements (e.g. tool/model failure events requiring error metadata).
    missing_fields: list[str] = []
    if trace.family == "learner" and trace.actor_user_id is None:
        missing_fields.append("actor_user_id")

    required_payload = REQUIRED_PAYLOAD_FIELDS.get(
        (trace.family, trace.event_type), set()
    )
    if required_payload:
        payload = trace.payload or {}
        for key in required_payload:
            if key not in payload or payload[key] is None:
                missing_fields.append(f"payload.{key}")

    if missing_fields:
        raise MissingTraceContextError(
            missing_fields=missing_fields,
            details={
                "family": trace.family,
                "event_type": trace.event_type,
                "session_id": str(trace.session_id),
                "missing_fields": missing_fields,
            },
        )

    if trace.event_index < 0:
        raise TraceValidationError(
            message="Trace event_index must be >= 0.",
            details={
                "session_id": str(trace.session_id),
                "event_index": trace.event_index,
            },
        )

    if trace.occurred_at.tzinfo is None or trace.occurred_at.utcoffset() is None:
        raise TraceValidationError(
            message="Trace occurred_at must be timezone-aware UTC datetime.",
            details={
                "session_id": str(trace.session_id),
                "occurred_at": trace.occurred_at.isoformat(),
            },
        )

    if trace.occurred_at.utcoffset() != timedelta(0):
        raise TraceValidationError(
            message="Trace occurred_at must be a UTC datetime.",
            details={
                "session_id": str(trace.session_id),
                "occurred_at": trace.occurred_at.isoformat(),
            },
        )

    repo.append_trace_event(trace=trace)
