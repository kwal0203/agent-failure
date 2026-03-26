from dataclasses import dataclass
from uuid import UUID
from typing import Literal
from datetime import datetime


TraceFamily = Literal["lifecycle", "learner", "runtime", "tool", "model"]


@dataclass(frozen=True)
class TraceEvent:
    event_id: UUID
    session_id: UUID
    family: TraceFamily
    event_type: str
    occurred_at: datetime
    source: str
    event_index: int
    payload: dict[str, object]
    trace_version: int = 1

    correlation_id: UUID | None = None
    request_id: UUID | None = None
    actor_user_id: UUID | None = None
    lab_id: UUID | None = None
    lab_version_id: UUID | None = None
