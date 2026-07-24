from datetime import datetime, timezone
from uuid import UUID, uuid4

from apps.control_plane.src.application.session_lifecycle.ports import UnitOfWork
from apps.control_plane.src.application.trace.service import append_trace_event
from apps.control_plane.src.application.trace.types import TraceEvent


def append_runtime_trace(
    *,
    uow: UnitOfWork,
    session_id: UUID,
    event_type: str,
    source: str,
    payload: dict[str, object],
    lab_id: UUID | None = None,
    lab_version_id: UUID | None = None,
    lab_difficulty: str | None = None,
) -> None:
    with uow.transaction():
        trace_event = TraceEvent(
            event_id=uuid4(),
            session_id=session_id,
            family="runtime",
            event_type=event_type,
            occurred_at=datetime.now(timezone.utc),
            source=source,
            event_index=uow.trace.get_next_event_index(session_id=session_id),
            payload=payload,
            trace_version=1,
            correlation_id=None,
            request_id=None,
            actor_user_id=None,
            lab_id=lab_id,
            lab_version_id=lab_version_id,
            lab_difficulty=lab_difficulty,
        )
        append_trace_event(trace=trace_event, repo=uow.trace, outbox_repo=uow.outbox)
