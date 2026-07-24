from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from apps.control_plane.src.application.common.types import (
    GetLabCatalogRow,
    LabRuntimeBinding,
)
from apps.control_plane.src.application.session_create.errors import (
    LabNotAvailableError,
)
from apps.control_plane.src.application.session_create.ports import (
    LabRepository,
)

from .models import LabModel, LabVersionModel


class SQLAlchemyLabRepository(LabRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_lab_catalog(self) -> list[GetLabCatalogRow]:
        has_active_version = exists(
            select(LabVersionModel.id).where(
                LabVersionModel.lab_id == LabModel.id,
                LabVersionModel.is_active.is_(True),
            )
        )
        rows = self._db.execute(
            select(
                LabModel.id,
                LabModel.slug,
                LabModel.name,
                LabModel.summary,
                LabModel.supports_resume,
                LabModel.supports_uploads,
            )
            .where(
                LabModel.is_active.is_(True),
                LabModel.is_published.is_(True),
                has_active_version,
            )
            .order_by(
                LabModel.catalog_order.asc().nulls_last(),
                LabModel.name.asc(),
                LabModel.id.asc(),
            )
        ).all()

        return [
            GetLabCatalogRow(
                lab_id=row.id,
                slug=row.slug,
                name=row.name,
                summary=row.summary,
                supports_resume=row.supports_resume,
                supports_uploads=row.supports_uploads,
            )
            for row in rows
        ]

    def validate_lab(self, lab_id: UUID) -> bool:
        return (
            self._db.execute(
                select(LabModel.id)
                .join(LabVersionModel, LabVersionModel.lab_id == LabModel.id)
                .where(
                    LabModel.id == lab_id,
                    LabModel.is_active.is_(True),
                    LabModel.is_published.is_(True),
                    LabVersionModel.is_active.is_(True),
                )
                .limit(1)
            ).scalar_one_or_none()
            is not None
        )

    def get_runtime_binding(
        self, lab_id: UUID, lab_version_id: UUID | None
    ) -> LabRuntimeBinding:
        if lab_version_id is None:
            raise LabNotAvailableError(
                lab_id=lab_id,
                details={"lab_id": str(lab_id), "reason": "NO_ACTIVE_LAB_VERSION"},
            )

        row = (
            self._db.execute(
                select(
                    LabModel.slug.label("lab_slug"),
                    LabVersionModel.version.label("lab_version"),
                )
                .join(LabVersionModel, LabVersionModel.lab_id == LabModel.id)
                .where(
                    LabModel.id == lab_id,
                    LabVersionModel.id == lab_version_id,
                    LabModel.is_active.is_(True),
                    LabVersionModel.is_active.is_(True),
                )
                .limit(1)
            )
            .mappings()
            .one_or_none()
        )

        if row is None:
            raise LabNotAvailableError(
                lab_id=lab_id,
                details={"lab_id": str(lab_id), "reason": "NO_ACTIVE_LAB_VERSION"},
            )

        return LabRuntimeBinding(
            lab_slug=row["lab_slug"], lab_version=row["lab_version"]
        )

    def get_active_version_id(self, lab_id: UUID) -> UUID | None:
        return self._db.execute(
            select(LabVersionModel.id)
            .join(LabModel, LabModel.id == LabVersionModel.lab_id)
            .where(
                LabVersionModel.lab_id == lab_id,
                LabModel.is_active.is_(True),
                LabModel.is_published.is_(True),
                LabVersionModel.is_active.is_(True),
            )
            .order_by(LabVersionModel.created_at.desc(), LabVersionModel.id.asc())
            .limit(1)
        ).scalar_one_or_none()
