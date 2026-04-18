from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.evaluator.src.application.ports import EvaluatorLabLookupPort
from apps.evaluator.src.application.types import EvaluatorLabRuntimeBinding
from apps.control_plane.src.infrastructure.persistence.models import (
    LabModel,
    LabVersionModel,
)


class SQLAlchemyEvaluatorLabLookupRepository(EvaluatorLabLookupPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_runtime_binding(
        self, lab_id: UUID, lab_version_id: UUID
    ) -> EvaluatorLabRuntimeBinding:
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
            raise ValueError(
                f"No runtime binding found for lab_id={lab_id}, lab_version_id={lab_version_id}"
            )

        return EvaluatorLabRuntimeBinding(
            lab_slug=row["lab_slug"],
            lab_version=row["lab_version"],
        )
