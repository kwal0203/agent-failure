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


@dataclass(frozen=True)
class EvaluatorTaskInput:
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    evaluator_version: int
    start_event_index: int
    end_event_index: int


@dataclass(frozen=True)
class EvaluatorFinding:
    result_type: ResultType
    code: str  # constraint_id or signal_id
    trigger_event_index: int | None
    trigger_start_event_index: int | None
    trigger_end_event_index: int | None
    feedback_level: FeedbackLevel
    reason_code: str
    feedback_payload: dict[str, object]


@dataclass(frozen=True)
class EvaluatorRunResult:
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    evaluator_version: int
    start_event_index: int
    end_event_index: int
    evaluated_event_count: int
    findings_count: int
    no_op: bool
    findings: tuple[EvaluatorFinding, ...]


@dataclass(frozen=True)
class EvaluatorTraceEvent:
    event_id: UUID
    session_id: UUID
    family: str
    event_type: str
    occurred_at: datetime
    source: str
    event_index: int
    payload: dict[str, object]
    trace_version: int
    correlation_id: UUID | None
    request_id: UUID | None
    actor_user_id: UUID | None
    lab_id: UUID | None
    lab_version_id: UUID | None


@dataclass(frozen=True)
class EvaluatorOnceResult:
    claimed_count: int
    succeeded_count: int
    failed_count: int
    retried_count: int
