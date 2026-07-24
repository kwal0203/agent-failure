from typing import Protocol
from uuid import UUID
from datetime import datetime

from .types import TraceEvent


class TraceEventPort(Protocol):
    def append_trace_event(self, trace: TraceEvent) -> None: ...

    def list_trace_events_for_session(
        self, session_id: UUID
    ) -> tuple[TraceEvent, ...]: ...

    def get_next_event_index(self, session_id: UUID) -> int: ...


class TraceOutboxPort(Protocol):
    def enqueue_for_evaluator(
        self,
        *,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        start_event_index: int,
        end_event_index: int,
        requested_at: datetime | None = None,
    ) -> None: ...
