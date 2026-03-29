from typing import Protocol
from uuid import UUID
from datetime import datetime

from .types import TraceEvent


class TraceEventPort(Protocol):
    def append_trace_event(self, trace: TraceEvent) -> None: ...

    def get_next_event_index(self, session_id: UUID) -> int: ...


class TraceOutboxPort(Protocol):
    def enqueue_for_evaluator(
        self,
        *,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        evaluator_version: int,
        start_event_index: int,
        end_event_index: int,
        requested_at: datetime | None = None,
    ) -> None: ...


# def append_trace_event(
#     trace: TraceEvent,
#     repo: TraceEventPort,
#     outbox_repo: TraceOutboxPort,
# ) -> None:
#     ...
