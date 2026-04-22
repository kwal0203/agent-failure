from typing import Literal, TypeAlias
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


CompletionStatus: TypeAlias = Literal[
    "in_progress", "completed_success", "completed_failure"
]

COMPLETION_STATUS_IN_PROGRESS: CompletionStatus = "in_progress"
COMPLETION_STATUS_COMPLETED_SUCCESS: CompletionStatus = "completed_success"
COMPLETION_STATUS_COMPLETED_FAILURE: CompletionStatus = "completed_failure"

TERMINAL_COMPLETION_STATUSES: tuple[CompletionStatus, ...] = (
    COMPLETION_STATUS_COMPLETED_SUCCESS,
    COMPLETION_STATUS_COMPLETED_FAILURE,
)


@dataclass(frozen=True)
class PendingSessionCompletedEvent:
    outbox_event_id: UUID
    session_id: UUID
    payload: dict[str, object]
    attempt_count: int
    requested_at: datetime


@dataclass(frozen=True)
class SessionCompletionProjectionOnceResult:
    claimed_count: int
    succeeded_count: int
    failed_count: int
    retried_count: int


@dataclass(frozen=True)
class SessionCompletionState:
    completion_status: CompletionStatus
    completed_at: datetime | None
    completion_reason_code: str | None
