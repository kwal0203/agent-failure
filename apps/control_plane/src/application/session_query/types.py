from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
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


@dataclass
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
