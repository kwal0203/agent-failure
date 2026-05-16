from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class CreatePilotRequestInput:
    full_name: str
    work_email: str
    university: str
    role: str | None = None
    course_name: str | None = None
    cohort_size: int | None = None
    notes: str | None = None
    source_ip: str | None = None


@dataclass(frozen=True)
class PilotRequestRecord:
    id: UUID
    status: str
    created_at: datetime


@dataclass(frozen=True)
class CreatePilotRequestResult:
    accepted: bool
    request: PilotRequestRecord | None = None
    error: str | None = None
    error_code: str | None = None
