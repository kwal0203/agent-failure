from uuid import UUID
from sqlalchemy.orm import Session

from apps.control_plane.src.application.session_create.ports import (
    LabRepository,
    LabRuntimeBinding,
)


class PostgresLabRepository(LabRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def validate_lab(self, lab_id: UUID) -> bool:
        # TODO: Replace with DB-backed published-lab lookup when labs table exists.
        _ = lab_id
        return True

    def get_runtime_binding(
        self, lab_id: UUID, lab_version_id: UUID | None
    ) -> LabRuntimeBinding:
        # TODO(E4 follow-up): replace hardcoded mapping with DB-backed lab/lab_version lookup.
        _ = (lab_id, lab_version_id)
        return LabRuntimeBinding(lab_slug="baseline", lab_version="0.1.0")
