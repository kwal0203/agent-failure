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
    # NOTE(P1-E6-T3): runtime/tool/model are intentionally empty in T3 and will
    # reject all event types for those families until P1-E6-T4 extends support.
    "lifecycle": {"SESSION_CREATED", "SESSION_TRANSITIONED"},
    "learner": {"USER_PROMPT_SUBMITTED"},
    "runtime": set(),
    "tool": set(),
    "model": set(),
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
            },
        )

    missing_fields: list[str] = []
    if trace.family == "learner" and trace.actor_user_id is None:
        missing_fields.append("actor_user_id")

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
