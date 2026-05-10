from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select

from apps.control_plane.src.application.session_create.ports import (
    LabRepository,
)
from apps.control_plane.src.application.session_create.errors import (
    LabNotAvailableError,
)
from apps.control_plane.src.application.common.types import (
    GetLabCatalogRow,
    LabRuntimeBinding,
)

from .models import LabVersionModel, LabModel


class SQLAlchemyLabRepository(LabRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_lab_catalog(self) -> list[GetLabCatalogRow]:
        # TODO(P2 follow-up): replace this stubbed catalog with a real SELECT against
        # a labs table (published + launchable rows) once lab metadata is persisted.
        lab_rows: list[GetLabCatalogRow] = [
            GetLabCatalogRow(
                lab_id=UUID("44444444-4444-4444-4444-444444444444"),
                slug="agent-prompt-injection",
                name="Indirect Prompt Injection",
                summary="Attack an agent using indirect prompt injection via a malicious email.",
                supports_resume=False,
                supports_uploads=False,
            ),
            GetLabCatalogRow(
                lab_id=UUID("55555555-5555-5555-5555-555555555555"),
                slug="agent-tool-misuse",
                name="Tool Misuse",
                summary="Induce an LLM agent into unsafe tool operations via deceptive inputs.",
                supports_resume=False,
                supports_uploads=False,
            ),
            GetLabCatalogRow(
                lab_id=UUID("66666666-6666-6666-6666-666666666666"),
                slug="agent-memory-poisoning",
                name="Memory Poisoning",
                summary="Poison an LLM agent's memory to reroute invoice payments to an attacker-controlled account.",
                supports_resume=False,
                supports_uploads=False,
            ),
        ]
        return lab_rows

    def validate_lab(self, lab_id: UUID) -> bool:
        # TODO: Replace with DB-backed published-lab lookup when labs table exists.
        _ = lab_id
        return True

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
        row = self._db.execute(
            select(LabVersionModel.id)
            .where(
                LabVersionModel.lab_id == lab_id,
                LabVersionModel.is_active.is_(True),
            )
            .limit(1)
        ).scalar_one_or_none()
        return row
