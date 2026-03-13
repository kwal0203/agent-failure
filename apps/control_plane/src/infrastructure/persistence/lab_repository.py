from uuid import UUID
from sqlalchemy.orm import Session

from apps.control_plane.src.application.session_create.ports import LabRepository


class PostgresLabRepository(LabRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def validate_lab(self, lab_id: UUID) -> bool:
        # TODO: Replace with DB-backed published-lab lookup when labs table exists.
        return True
