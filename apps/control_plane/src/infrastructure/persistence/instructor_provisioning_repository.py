from uuid import UUID

from sqlalchemy.orm import Session

from apps.control_plane.src.application.instructor_provisioning.ports import (
    InstructorProvisioningRepositoryPort,
)
from apps.control_plane.src.application.instructor_provisioning.types import (
    InstructorCourseMembershipRecord,
    PilotProvisionContext,
)
from apps.control_plane.src.infrastructure.persistence.models import (
    InstructorCourseMembershipModel,
    PilotRequestProvisionModel,
)


class SQLAlchemyInstructorProvisioningRepository(InstructorProvisioningRepositoryPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_pilot_provision_context(
        self, *, pilot_request_id: UUID
    ) -> PilotProvisionContext | None:
        row = (
            self._db.query(PilotRequestProvisionModel)
            .filter(PilotRequestProvisionModel.pilot_request_id == pilot_request_id)
            .one_or_none()
        )
        if row is None:
            return None
        return PilotProvisionContext(
            pilot_request_id=row.pilot_request_id,
            course_id=row.course_id,
            course_name=row.course_name,
            instructor_email=row.instructor_email,
        )

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
    ) -> tuple[InstructorCourseMembershipRecord, bool]:
        row = (
            self._db.query(InstructorCourseMembershipModel)
            .filter(
                InstructorCourseMembershipModel.instructor_email == instructor_email,
                InstructorCourseMembershipModel.course_id == course_id,
            )
            .one_or_none()
        )
        if row is None:
            row = InstructorCourseMembershipModel(
                pilot_request_id=pilot_request_id,
                instructor_email=instructor_email,
                instructor_user_id=instructor_user_id,
                course_id=course_id,
                course_name=course_name,
                provisioned_by=provisioned_by,
                provisioning_correlation_id=provisioning_correlation_id,
            )
            self._db.add(row)
            self._db.flush()
            created = True
        else:
            if row.instructor_user_id is None and instructor_user_id is not None:
                row.instructor_user_id = instructor_user_id
            if row.provisioned_by is None and provisioned_by is not None:
                row.provisioned_by = provisioned_by
            if (
                row.provisioning_correlation_id is None
                and provisioning_correlation_id is not None
            ):
                row.provisioning_correlation_id = provisioning_correlation_id
            created = False

        return (
            InstructorCourseMembershipRecord(
                id=row.id,
                instructor_email=row.instructor_email,
                course_id=row.course_id,
                course_name=row.course_name,
                pilot_request_id=row.pilot_request_id,
                instructor_user_id=row.instructor_user_id,
                provisioned_by=row.provisioned_by,
                provisioning_correlation_id=row.provisioning_correlation_id,
                created_at=row.created_at,
            ),
            created,
        )

    def commit(self) -> None:
        self._db.commit()
