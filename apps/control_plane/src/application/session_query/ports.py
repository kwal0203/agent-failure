from typing import Protocol
from uuid import UUID
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SessionMetadataDTO:
    id: UUID
    lab_id: UUID | None
    lab_version_id: UUID | None
    state: str
    runtime_substate: str | None
    resume_mode: str
    interactive: bool
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None


class SessionMetadataRepository(Protocol):
    def get_session_metadata(self, session_id: UUID) -> SessionMetadataDTO | None: ...
