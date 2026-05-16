from datetime import datetime

from sqlalchemy.orm import Session

from apps.control_plane.src.application.pilot_requests.ports import (
    PilotRequestRepositoryPort,
)
from apps.control_plane.src.application.pilot_requests.types import (
    CreatePilotRequestInput,
    PilotRequestRecord,
)
from apps.control_plane.src.infrastructure.persistence.models import PilotRequestModel


class SQLAlchemyPilotRequestRepository(PilotRequestRepositoryPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def count_recent_by_work_email(self, *, work_email: str, since: datetime) -> int:
        return (
            self._db.query(PilotRequestModel)
            .filter(
                PilotRequestModel.work_email == work_email,
                PilotRequestModel.created_at >= since,
            )
            .count()
        )

    def count_recent_by_source_ip(self, *, source_ip: str, since: datetime) -> int:
        return (
            self._db.query(PilotRequestModel)
            .filter(
                PilotRequestModel.source_ip == source_ip,
                PilotRequestModel.created_at >= since,
            )
            .count()
        )

    def exists_recent_duplicate(
        self, *, work_email: str, university: str, since: datetime
    ) -> bool:
        row = (
            self._db.query(PilotRequestModel.id)
            .filter(
                PilotRequestModel.work_email == work_email,
                PilotRequestModel.university == university,
                PilotRequestModel.created_at >= since,
            )
            .first()
        )
        return row is not None

    def create_pilot_request(
        self, request: CreatePilotRequestInput
    ) -> PilotRequestRecord:
        row = PilotRequestModel(
            full_name=request.full_name,
            work_email=request.work_email,
            university=request.university,
            role=request.role,
            course_name=request.course_name,
            cohort_size=request.cohort_size,
            notes=request.notes,
            source_ip=request.source_ip,
            status="new",
        )
        self._db.add(row)
        self._db.flush()
        return PilotRequestRecord(
            id=row.id,
            full_name=row.full_name,
            work_email=row.work_email,
            university=row.university,
            role=row.role,
            course_name=row.course_name,
            cohort_size=row.cohort_size,
            notes=row.notes,
            source_ip=row.source_ip,
            status=row.status,
            created_at=row.created_at,
        )

    def list_pilot_requests(
        self,
        *,
        status: str | None,
        created_after: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[PilotRequestRecord, ...]:
        query = self._db.query(PilotRequestModel).order_by(
            PilotRequestModel.created_at.desc()
        )
        if status is not None:
            query = query.filter(PilotRequestModel.status == status)
        if created_after is not None:
            query = query.filter(PilotRequestModel.created_at > created_after)

        rows = query.offset(offset).limit(limit).all()
        return tuple(
            PilotRequestRecord(
                id=row.id,
                full_name=row.full_name,
                work_email=row.work_email,
                university=row.university,
                role=row.role,
                course_name=row.course_name,
                cohort_size=row.cohort_size,
                notes=row.notes,
                source_ip=row.source_ip,
                status=row.status,
                created_at=row.created_at,
            )
            for row in rows
        )

    def commit(self) -> None:
        self._db.commit()
