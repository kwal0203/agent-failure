from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias
from uuid import UUID


CompletionStatus: TypeAlias = Literal[
    "in_progress",
    "completed_success",
    "completed_failure",
]

ObjectiveStatus: TypeAlias = Literal["pending", "complete"]


@dataclass(frozen=True)
class CompletionPolicyObjectiveRow:
    objective_key: str
    status: ObjectiveStatus
    required: bool = True


@dataclass(frozen=True)
class SessionObjectiveStateRow:
    objective_key: str
    status: ObjectiveStatus


@dataclass(frozen=True)
class LabObjectiveTemplateRow:
    objective_key: str
    sort_order: int
    required: bool = True


@dataclass(frozen=True)
class CompletionPolicyInput:
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    objectives: tuple[CompletionPolicyObjectiveRow, ...]


@dataclass(frozen=True)
class CompletionPolicyDecision:
    completion_status: CompletionStatus
    completed_at: datetime | None
    completion_reason_code: str | None
    decision_metadata: dict[str, object]
