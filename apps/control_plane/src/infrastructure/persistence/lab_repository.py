from uuid import UUID
from sqlalchemy.orm import Session

from apps.control_plane.src.application.session_create.ports import (
    LabRepository,
)

from apps.control_plane.src.application.common.types import (
    GetLabCatalogRow,
    LabRuntimeBinding,
)


class SQLAlchemyLabRepository(LabRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_lab_catalog(self) -> list[GetLabCatalogRow]:
        # TODO(P2 follow-up): replace this stubbed catalog with a real SELECT against
        # a labs table (published + launchable rows) once lab metadata is persisted.
        lab_rows: list[GetLabCatalogRow] = [
            GetLabCatalogRow(
                lab_id=UUID("11111111-1111-1111-1111-111111111111"),
                slug="prompt-injection",
                name="Prompt Injection",
                summary="Practice identifying and exploiting prompt-injection paths, then apply guardrails to contain them.",
                supports_resume=False,
                supports_uploads=False,
            ),
            GetLabCatalogRow(
                lab_id=UUID("22222222-2222-2222-2222-222222222222"),
                slug="rag-poisoning",
                name="RAG Poisoning",
                summary="Explore how poisoned retrieval content can steer agent behavior and test mitigation strategies.",
                supports_resume=False,
                supports_uploads=False,
            ),
            GetLabCatalogRow(
                lab_id=UUID("33333333-3333-3333-3333-333333333333"),
                slug="tool-misuse",
                name="Tool Misuse",
                summary="Detect unsafe tool invocation patterns and enforce constraints to prevent high-impact misuse.",
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
        # TODO(E4 follow-up): replace hardcoded mapping with DB-backed lab/lab_version lookup.
        _ = (lab_id, lab_version_id)
        return LabRuntimeBinding(lab_slug="baseline", lab_version="0.1.0")
