from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True)
class PilotRequestNotification:
    request_id: UUID
    status: str
    created_at: datetime
    full_name: str
    work_email: str
    university: str
    role: str | None = None
    course_name: str | None = None
    cohort_size: int | None = None
    notes: str | None = None
    source_ip: str | None = None


class PilotRequestNotifierPort(Protocol):
    def notify(self, payload: PilotRequestNotification) -> None: ...
