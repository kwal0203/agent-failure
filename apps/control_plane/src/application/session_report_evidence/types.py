from dataclasses import dataclass
from datetime import datetime
from typing import Literal, TypeAlias
from uuid import UUID


TraceEvidenceType: TypeAlias = Literal[
    "exploit_step",
    "exploit_outcome",
    "system_context",
    "coaching_feedback",
    "noise",
]
TraceEvidencePriority: TypeAlias = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class SessionReportEvidenceItemInput:
    event_id: UUID
    position: int
    title: str
    description: str | None
    occurred_at: datetime
    evidence_type: TraceEvidenceType
    objective_keys: tuple[str, ...]
    why_it_matters: str | None
    default_priority: TraceEvidencePriority
    student_note: str | None


@dataclass(frozen=True)
class SessionReportEvidenceRow:
    id: UUID
    session_id: UUID
    event_id: UUID
    position: int
    title: str
    description: str | None
    occurred_at: datetime
    evidence_type: TraceEvidenceType
    objective_keys: tuple[str, ...]
    why_it_matters: str | None
    default_priority: TraceEvidencePriority
    student_note: str | None
    created_at: datetime
    updated_at: datetime
