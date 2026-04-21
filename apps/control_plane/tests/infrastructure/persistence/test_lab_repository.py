from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from apps.control_plane.src.infrastructure.persistence.lab_repository import (
    SQLAlchemyLabRepository,
)
from apps.control_plane.src.infrastructure.persistence.models import (
    LabModel,
    LabVersionModel,
)


LAB_3_ID = UUID("33333333-3333-3333-3333-333333333333")
LAB_3_VERSION_ID = UUID("33333333-3333-3333-3333-aaaaaaaaaaa3")


@pytest.mark.usefixtures("engine")
def test_get_runtime_binding_returns_expected_lab3_mapping(db_session: Session) -> None:
    db_session.add(
        LabModel(
            id=LAB_3_ID,
            slug="memory-poisoning",
            name="Memory Poisoning",
            summary="test",
            is_active=True,
        )
    )
    db_session.add(
        LabVersionModel(
            id=LAB_3_VERSION_ID,
            lab_id=LAB_3_ID,
            version="v1",
            is_active=True,
        )
    )
    db_session.commit()

    repo = SQLAlchemyLabRepository(db=db_session)
    binding = repo.get_runtime_binding(lab_id=LAB_3_ID, lab_version_id=LAB_3_VERSION_ID)

    assert binding.lab_slug == "memory-poisoning"
    assert binding.lab_version == "v1"
