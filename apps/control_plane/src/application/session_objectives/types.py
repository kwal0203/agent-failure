from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PendingSessionObjectiveCompletedEvent:
    outbox_event_id: UUID
    session_id: UUID
    payload: dict[str, object]
    attempt_count: int
    requested_at: datetime


@dataclass(frozen=True)
class SessionObjectiveProjectionOnceResult:
    claimed_count: int
    succeeded_count: int
    failed_count: int
    retried_count: int
