from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemyTraceEventRepository,
)
from apps.control_plane.src.application.trace.types import TraceFamily, TraceEvent

from uuid import uuid4, UUID
from datetime import datetime, timezone


def build_trace_event(
    *,
    trace_repo: SQLAlchemyTraceEventRepository,
    session_id: UUID,
    family: TraceFamily,
    event_type: str,
    source: str,
    payload: dict[str, object],
    correlation_id: UUID | None = None,
    request_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    lab_id: UUID | None = None,
    lab_version_id: UUID | None = None,
) -> TraceEvent:

    return TraceEvent(
        event_id=uuid4(),
        session_id=session_id,
        family=family,
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
        source=source,
        event_index=trace_repo.get_next_event_index(session_id=session_id),
        payload=payload,
        trace_version=1,
        correlation_id=correlation_id,
        request_id=request_id,
        actor_user_id=actor_user_id,
        lab_id=lab_id,
        lab_version_id=lab_version_id,
    )


def build_model_turn_failed_payload(
    *,
    error_code: str,
    phase: str,
    turn_start: datetime,
    chunks_emitted: int,
    provider: str = "openrouter",
) -> dict[str, object]:
    return {
        "provider": provider,
        "error_code": error_code,
        "retryable": True,
        "phase": phase,
        "duration_ms": int(
            (datetime.now(timezone.utc) - turn_start).total_seconds() * 1000
        ),
        "chunks_emitted": chunks_emitted,
    }
