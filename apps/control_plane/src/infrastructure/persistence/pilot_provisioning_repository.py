from uuid import UUID

from sqlalchemy.orm import Session

from apps.control_plane.src.application.pilot_provisioning.ports import (
    PilotProvisioningRepositoryPort,
)
from apps.control_plane.src.application.pilot_provisioning.types import (
    PilotProvisionRecord,
    ProvisionPilotRequestInput,
)
from apps.control_plane.src.infrastructure.persistence.models import (
    ClassCodeModel,
    PilotRequestModel,
    PilotRequestProvisionModel,
)


class SQLAlchemyPilotProvisioningRepository(PilotProvisioningRepositoryPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def pilot_request_exists(self, *, request_id: UUID) -> bool:
        row = (
            self._db.query(PilotRequestModel.id)
            .filter(PilotRequestModel.id == request_id)
            .one_or_none()
        )
        return row is not None

    def get_provision_by_pilot_request_id(
        self, *, request_id: UUID
    ) -> PilotProvisionRecord | None:
        row = (
            self._db.query(PilotRequestProvisionModel)
            .filter(PilotRequestProvisionModel.pilot_request_id == request_id)
            .one_or_none()
        )
        if row is None:
            return None
        class_code = (
            self._db.query(ClassCodeModel)
            .filter(ClassCodeModel.code == row.class_code)
            .one_or_none()
        )
        if class_code is None:
            raise ValueError("Provision references missing class code.")
        return PilotProvisionRecord(
            id=row.id,
            pilot_request_id=row.pilot_request_id,
            course_id=row.course_id,
            course_name=row.course_name,
            class_code=row.class_code,
            instructor_email=row.instructor_email,
            class_code_id=class_code.id,
            provisioned_by=row.provisioned_by,
            provisioning_correlation_id=row.provisioning_correlation_id,
            class_code_status=class_code.status,
            class_code_max_uses=class_code.max_uses,
            created_at=row.created_at,
        )

    def create_or_get_provision(
        self, *, request: ProvisionPilotRequestInput
    ) -> tuple[PilotProvisionRecord, bool]:
        existing = self.get_provision_by_pilot_request_id(
            request_id=request.pilot_request_id
        )
        if existing is not None:
            if (
                existing.course_id != request.course_id
                or existing.course_name != request.course_name
                or existing.class_code != request.class_code
                or existing.instructor_email != request.instructor_email
            ):
                raise ValueError(
                    "Pilot request already provisioned with different values."
                )
            return existing, False

        class_code_row = (
            self._db.query(ClassCodeModel)
            .filter(ClassCodeModel.code == request.class_code)
            .one_or_none()
        )
        if class_code_row is None:
            class_code_row = ClassCodeModel(
                code=request.class_code,
                course_id=request.course_id,
                course_name=request.course_name,
                max_uses=request.max_uses,
                status="active",
            )
            self._db.add(class_code_row)
            self._db.flush()
        else:
            if (
                class_code_row.course_id != request.course_id
                or class_code_row.course_name != request.course_name
            ):
                raise ValueError(
                    "Class code already exists and is bound to a different course."
                )
            if request.max_uses is not None and class_code_row.max_uses is None:
                class_code_row.max_uses = request.max_uses

        provision_row = PilotRequestProvisionModel(
            pilot_request_id=request.pilot_request_id,
            course_id=request.course_id,
            course_name=request.course_name,
            class_code=request.class_code,
            class_code_id=class_code_row.id,
            instructor_email=request.instructor_email,
            provisioned_by=request.provisioned_by,
            provisioning_correlation_id=request.provisioning_correlation_id,
        )
        self._db.add(provision_row)
        self._db.flush()
        return (
            PilotProvisionRecord(
                id=provision_row.id,
                pilot_request_id=provision_row.pilot_request_id,
                course_id=provision_row.course_id,
                course_name=provision_row.course_name,
                class_code=provision_row.class_code,
                instructor_email=provision_row.instructor_email,
                class_code_id=class_code_row.id,
                provisioned_by=provision_row.provisioned_by,
                provisioning_correlation_id=provision_row.provisioning_correlation_id,
                class_code_status=class_code_row.status,
                class_code_max_uses=class_code_row.max_uses,
                created_at=provision_row.created_at,
            ),
            True,
        )

    def commit(self) -> None:
        self._db.commit()
