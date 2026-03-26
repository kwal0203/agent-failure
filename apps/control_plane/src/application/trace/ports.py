from typing import Protocol
from uuid import UUID

from .types import TraceEvent


class TraceEventPort(Protocol):
    def append_trace_event(self, trace: TraceEvent) -> None: ...

    def get_next_event_index(self, session_id: UUID) -> int: ...
