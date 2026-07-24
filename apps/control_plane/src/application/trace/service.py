from datetime import timedelta
from typing import Iterable
from apps.contracts.src.runtime_trace import (
    ALLOWED_EVENT_TYPES,
    REQUIRED_PAYLOAD_FIELDS,
)

from .ports import TraceEventPort, TraceOutboxPort
from .types import TraceEvent
from .errors import (
    UnknownTraceFamilyError,
    UnknownTraceEventTypeError,
    MissingTraceContextError,
    TraceValidationError,
)
from .visibility import LEARNER_VISIBLE_ALLOWLIST


def _trace_error_details(trace: TraceEvent, **extra: object) -> dict[str, object]:
    details: dict[str, object] = {
        "family": trace.family,
        "event_type": trace.event_type,
        "session_id": str(trace.session_id),
        "source": trace.source,
        "trace_version": trace.trace_version,
        "event_index": trace.event_index,
        "occurred_at": trace.occurred_at.isoformat(),
    }
    details.update(extra)
    return details


def append_trace_event(
    trace: TraceEvent, repo: TraceEventPort, outbox_repo: TraceOutboxPort
) -> None:

    if trace.family not in ALLOWED_EVENT_TYPES:
        raise UnknownTraceFamilyError(
            family=trace.family,
            details=_trace_error_details(
                trace,
                allowed_families=sorted(ALLOWED_EVENT_TYPES),
            ),
        )

    if trace.event_type not in ALLOWED_EVENT_TYPES[trace.family]:
        raise UnknownTraceEventTypeError(
            family=trace.family,
            event_type=trace.event_type,
            details=_trace_error_details(
                trace=trace,
                allowed_event_types=sorted(ALLOWED_EVENT_TYPES[trace.family]),
            ),
        )

    # Context validation is deliberately schema-driven. Learner events require
    # actor attribution, while event-specific payload requirements live in
    # REQUIRED_PAYLOAD_FIELDS below.
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
            details=_trace_error_details(trace=trace, missing_fields=missing_fields),
        )

    if trace.event_index < 0:
        raise TraceValidationError(
            message="Trace event_index must be >= 0.",
            details=_trace_error_details(trace=trace),
        )

    if trace.occurred_at.tzinfo is None or trace.occurred_at.utcoffset() is None:
        raise TraceValidationError(
            message="Trace occurred_at must be timezone-aware UTC datetime.",
            details=_trace_error_details(trace=trace),
        )

    if trace.occurred_at.utcoffset() != timedelta(0):
        raise TraceValidationError(
            message="Trace occurred_at must be a UTC datetime.",
            details=_trace_error_details(trace=trace),
        )

    repo.append_trace_event(trace=trace)

    # NOTE: Only enqueue evaluator traces/events at the end of a turn
    if trace.event_type not in {"MODEL_TURN_COMPLETED", "MODEL_TURN_FAILED"}:
        return

    if trace.lab_id is None or trace.lab_version_id is None:
        return

    outbox_repo.enqueue_for_evaluator(
        session_id=trace.session_id,
        lab_id=trace.lab_id,
        lab_version_id=trace.lab_version_id,
        start_event_index=trace.event_index,
        end_event_index=trace.event_index,
    )


def project_learner_visible_events(
    events: Iterable[TraceEvent],
) -> tuple[TraceEvent, ...]:
    projected: list[TraceEvent] = []
    for event in events:
        if (event.family, event.event_type) in LEARNER_VISIBLE_ALLOWLIST:
            projected.append(event)

    return tuple(projected)
