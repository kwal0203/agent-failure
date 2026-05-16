from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ProvisionPilotRequestInput:
    pilot_request_id: UUID
    course_id: str
    course_name: str
    class_code: str
    instructor_email: str
    max_uses: int | None = None
    provisioned_by: UUID | None = None
    provisioning_correlation_id: str | None = None


@dataclass(frozen=True)
class PilotProvisionRecord:
    id: UUID
    pilot_request_id: UUID
    course_id: str
    course_name: str
    class_code: str
    instructor_email: str
    class_code_id: UUID
    provisioned_by: UUID | None
    provisioning_correlation_id: str | None
    class_code_status: str
    class_code_max_uses: int | None
    created_at: datetime


@dataclass(frozen=True)
class ProvisionPilotRequestSummary:
    pilot_request_id: UUID
    course_id: str
    course_name: str
    class_code: str
    class_code_id: UUID
    class_code_status: str
    class_code_max_uses: int | None
    instructor_email: str
    provisioned_by: UUID | None
    provisioning_correlation_id: str | None
    provisioned_at: datetime


@dataclass(frozen=True)
class ProvisionPilotRequestResult:
    ok: bool
    summary: ProvisionPilotRequestSummary | None = None
    created: bool = False
    error: str | None = None
    error_code: str | None = None
