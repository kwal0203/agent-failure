from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import cast, TypeAlias, Literal


ProgressStatus: TypeAlias = Literal["pending", "complete"]


@dataclass(frozen=True)
class SessionObjectiveRow:
    objective_key: str
    label: str
    status: ProgressStatus
    completed_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True)
class SessionMetadataRow:
    id: UUID
    lab_id: UUID | None
    lab_version_id: UUID | None
    owner_user_id: UUID
    state: str
    runtime_substate: str | None
    resume_mode: str
    last_transition_reason: str | None
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None
    lab_difficulty: str = "medium"


@dataclass(frozen=True)
class SessionObjectiveDTO:
    objective_key: str
    label: str
    status: ProgressStatus
    completed_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True)
class SessionMetadataDTO:
    id: UUID
    lab_id: UUID | None
    lab_version_id: UUID | None
    owner_user_id: UUID
    state: str
    runtime_substate: str | None
    resume_mode: str
    last_transition_reason: str | None
    interactive: bool
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None
    lab_difficulty: str = "medium"
    progress_chips: list[SessionObjectiveDTO] = field(
        default_factory=lambda: cast(list[SessionObjectiveDTO], [])
    )


@dataclass(frozen=True)
class SessionMetadataBundleRow:
    metadata: SessionMetadataRow
    objectives: list[SessionObjectiveRow]
