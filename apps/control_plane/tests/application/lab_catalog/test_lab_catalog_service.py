from uuid import UUID, uuid4

import pytest

from apps.control_plane.src.application.common.errors import ForbiddenError
from apps.control_plane.src.application.common.types import (
    GetLabCatalogRow,
    LabRuntimeBinding,
    PrincipalContext,
)
from apps.control_plane.src.application.lab_catalog.service import (
    get_labs_for_principal,
)


class StubLabRepository:
    def __init__(self, rows: list[GetLabCatalogRow]) -> None:
        self._rows = rows

    def get_lab_catalog(self) -> list[GetLabCatalogRow]:
        return self._rows

    def validate_lab(self, lab_id: UUID) -> bool:
        _ = lab_id
        return True

    def get_runtime_binding(
        self, lab_id: UUID, lab_version_id: UUID | None
    ) -> LabRuntimeBinding:
        _ = (lab_id, lab_version_id)
        return LabRuntimeBinding(lab_slug="baseline", lab_version="0.1.0")


def test_get_labs_for_principal_returns_mapped_catalog() -> None:
    first_id = uuid4()
    rows = [
        GetLabCatalogRow(
            lab_id=first_id,
            slug="prompt-injection",
            name="Prompt Injection",
            summary="Prompt injection lab",
            supports_resume=False,
            supports_uploads=False,
        ),
        GetLabCatalogRow(
            lab_id=uuid4(),
            slug="tool-misuse",
            name="Tool Misuse",
            summary="Tool misuse lab",
            supports_resume=True,
            supports_uploads=False,
        ),
    ]
    repo = StubLabRepository(rows=rows)
    principal = PrincipalContext(user_id=uuid4(), role="learner")

    result = get_labs_for_principal(principal=principal, lab_repo=repo)

    assert len(result.labs) == 2
    assert result.labs[0].lab_id == first_id
    assert result.labs[0].slug == "prompt-injection"
    assert result.labs[0].capabilities.supports_resume is False
    assert result.labs[1].capabilities.supports_resume is True


def test_get_labs_for_principal_allows_admin() -> None:
    repo = StubLabRepository(rows=[])
    principal = PrincipalContext(user_id=uuid4(), role="admin")

    result = get_labs_for_principal(principal=principal, lab_repo=repo)

    assert result.labs == []


def test_get_labs_for_principal_forbidden_for_unknown_role() -> None:
    repo = StubLabRepository(rows=[])
    principal = PrincipalContext(user_id=uuid4(), role="viewer")

    with pytest.raises(ForbiddenError):
        get_labs_for_principal(principal=principal, lab_repo=repo)
