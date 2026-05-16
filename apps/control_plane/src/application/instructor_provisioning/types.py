from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ProvisionInstructorInput:
    pilot_request_id: UUID
    instructor_email: str
    create_user_if_missing: bool = False
    provisioned_by: UUID | None = None
    provisioning_correlation_id: str | None = None


@dataclass(frozen=True)
class PilotProvisionContext:
    pilot_request_id: UUID
    course_id: str
    course_name: str
    instructor_email: str


@dataclass(frozen=True)
class InstructorCourseMembershipRecord:
    id: UUID
    instructor_email: str
    course_id: str
    course_name: str
    pilot_request_id: UUID
    instructor_user_id: str | None
    provisioned_by: UUID | None
    provisioning_correlation_id: str | None
    created_at: datetime


@dataclass(frozen=True)
class InstructorIdentityResult:
    email: str
    user_created: bool
    group_assigned: bool
    user_id: str | None = None


@dataclass(frozen=True)
class ProvisionInstructorSummary:
    pilot_request_id: UUID
    course_id: str
    course_name: str
    instructor_email: str
    user_created: bool
    group_assigned: bool
    instructor_user_id: str | None
    membership_created: bool
    provisioned_by: UUID | None
    provisioning_correlation_id: str | None
    provisioned_at: datetime


@dataclass(frozen=True)
class ProvisionInstructorResult:
    ok: bool
    summary: ProvisionInstructorSummary | None = None
    error: str | None = None
    error_code: str | None = None
