from dataclasses import dataclass
from datetime import datetime
from typing import Any
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
    details: dict[str, Any] | None
    occurred_at: datetime
    trace_version: int
    event_index: int
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
    details: dict[str, Any] | None
    occurred_at: datetime
    trace_version: int
    event_index: int
    evidence_type: TraceEvidenceType
    objective_keys: tuple[str, ...]
    why_it_matters: str | None
    default_priority: TraceEvidencePriority
    student_note: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ReportObjectiveMapping:
    objective_key: str
    label: str
    rubric_target: str


@dataclass(frozen=True)
class ReportEvidenceProjection:
    event_id: UUID
    position: int
    title: str
    description: str | None
    details: dict[str, Any] | None
    occurred_at: datetime
    trace_version: int
    event_index: int
    evidence_type: TraceEvidenceType
    objective_keys: tuple[str, ...]
    why_it_matters: str | None
    default_priority: TraceEvidencePriority
    citation_label: str
    objective_mapping: tuple[ReportObjectiveMapping, ...]
    evidence_strength: TraceEvidencePriority
    student_note: str | None
