from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from apps.control_plane.src.application.enrollment.ports import EnrollmentRepositoryPort
from apps.control_plane.src.application.enrollment.types import (
    ClassCodeRecord,
    EnrollmentTokenRecord,
)
from apps.control_plane.src.infrastructure.persistence.models import (
    ClassCodeModel,
    EnrollmentModel,
    EnrollmentTokenModel,
)


class SQLAlchemyEnrollmentRepository(EnrollmentRepositoryPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_class_code(self, code: str) -> ClassCodeRecord | None:
        row = (
            self._db.query(ClassCodeModel)
            .filter(ClassCodeModel.code == code)
            .one_or_none()
        )
        if row is None:
            return None
        return ClassCodeRecord(
            code=row.code,
            course_id=row.course_id,
            course_name=row.course_name,
            expires_at=row.expires_at,
            max_uses=row.max_uses,
            uses=row.uses,
            status=row.status,
        )

    def create_enrollment_token(
        self,
        *,
        nonce: str,
        email: str,
        course_id: str,
        course_name: str,
        expires_at_epoch_sec: int,
    ) -> None:
        self._db.add(
            EnrollmentTokenModel(
                nonce=nonce,
                email=email,
                course_id=course_id,
                course_name=course_name,
                expires_at=datetime.fromtimestamp(expires_at_epoch_sec, tz=UTC),
            )
        )

    def increment_class_code_uses(self, code: str) -> None:
        row = self._db.query(ClassCodeModel).filter(ClassCodeModel.code == code).one()
        row.uses = row.uses + 1

    def get_enrollment_token(self, nonce: str) -> EnrollmentTokenRecord | None:
        row = (
            self._db.query(EnrollmentTokenModel)
            .filter(EnrollmentTokenModel.nonce == nonce)
            .one_or_none()
        )
        if row is None:
            return None
        return EnrollmentTokenRecord(
            nonce=row.nonce,
            email=row.email,
            course_id=row.course_id,
            course_name=row.course_name,
            expires_at=row.expires_at,
            redeemed_at=row.redeemed_at,
        )

    def is_user_enrolled(self, *, user_id: UUID, course_id: str) -> bool:
        row = (
            self._db.query(EnrollmentModel)
            .filter(
                EnrollmentModel.user_id == user_id,
                EnrollmentModel.course_id == course_id,
            )
            .one_or_none()
        )
        return row is not None

    def mark_enrollment_token_redeemed(self, nonce: str) -> None:
        row = (
            self._db.query(EnrollmentTokenModel)
            .filter(EnrollmentTokenModel.nonce == nonce)
            .one()
        )
        row.redeemed_at = datetime.now(UTC)

    def create_enrollment(
        self,
        *,
        user_sub: str,
        user_id: UUID,
        email: str,
        course_id: str,
        course_name: str,
    ) -> None:
        self._db.add(
            EnrollmentModel(
                user_sub=user_sub,
                user_id=user_id,
                email=email,
                course_id=course_id,
                course_name=course_name,
                source="class_code",
            )
        )

    def commit(self) -> None:
        self._db.commit()
