from dataclasses import dataclass
from uuid import UUID
from typing import Literal
from datetime import datetime


ResultType = Literal[
    "constraint_violation",
    "success_signal",
    "partial_success",
    "no_effect",
    "terminal_outcome",
]
FeedbackLevel = Literal["none", "flag", "hint", "detailed_hint"]
FeedbackStatusType = Literal["learned", "progress", "no_progress", "session_terminal"]


@dataclass(frozen=True)
class LearnerEvaluatorFeedback:
    status: FeedbackStatusType
    reason_code: str
    evidence_snippet: str


@dataclass(frozen=True)
class EvaluatorPersistedResult:
    id: UUID
    idempotency_key: str
    result_type: ResultType
    code: str
    trigger_event_index: int | None
    trigger_start_event_index: int | None
    trigger_end_event_index: int | None
    feedback_level: FeedbackLevel
    reason_code: str
    feedback_payload: dict[str, object]
    created_at: datetime
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    evaluator_version: int


@dataclass(frozen=True)
class PendingLearnerFeedbackPublishEvent:
    outbox_event_id: UUID
    session_id: UUID
    attempt_count: int
    requested_at: datetime | None


@dataclass(frozen=True)
class LearnerFeedbackPublishResult:
    claimed_count: int
    succeeded_count: int
    failed_count: int
    retried_count: int
