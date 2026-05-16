from typing import Protocol
from uuid import UUID

from .types import (
    InstructorCourseMembershipRecord,
    InstructorIdentityResult,
    PilotProvisionContext,
)


class InstructorProvisioningRepositoryPort(Protocol):
    def get_pilot_provision_context(
        self, *, pilot_request_id: UUID
    ) -> PilotProvisionContext | None: ...

    def upsert_instructor_course_membership(
        self,
        *,
        pilot_request_id: UUID,
        instructor_email: str,
        instructor_user_id: str | None,
        course_id: str,
        course_name: str,
        provisioned_by: UUID | None,
        provisioning_correlation_id: str | None,
    ) -> tuple[InstructorCourseMembershipRecord, bool]: ...

    def commit(self) -> None: ...


class InstructorIdentityProviderPort(Protocol):
    def ensure_instructor_group_membership(
        self, *, email: str, create_user_if_missing: bool
    ) -> InstructorIdentityResult: ...
