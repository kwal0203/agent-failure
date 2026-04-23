from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias
from uuid import UUID


FeedbackSeverity: TypeAlias = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class SessionFeedbackCreateInput:
    session_id: UUID
    feedback_key: str
    reason_code: str
    message: str
    severity: FeedbackSeverity
    trigger_event_index: int | None
    created_at: datetime
    idempotency_key: str


@dataclass(frozen=True)
class SessionFeedbackRow:
    id: UUID
    session_id: UUID
    feedback_key: str
    reason_code: str
    message: str
    severity: FeedbackSeverity
    trigger_event_index: int | None
    created_at: datetime
    seen_at: datetime | None
    idempotency_key: str


@dataclass(frozen=True)
class SessionFeedbackListResult:
    rows: list[SessionFeedbackRow]
    unread_count: int


@dataclass(frozen=True)
class PendingSessionFeedbackCreatedEvent:
    outbox_event_id: UUID
    session_id: UUID
    payload: dict[str, object]
    attempt_count: int
    requested_at: datetime


@dataclass(frozen=True)
class SessionFeedbackProjectionOnceResult:
    claimed_count: int
    succeeded_count: int
    failed_count: int
    retried_count: int
