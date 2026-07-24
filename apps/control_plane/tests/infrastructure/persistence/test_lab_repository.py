from uuid import UUID, uuid4

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


def _add_lab(
    db_session: Session,
    *,
    lab_id: UUID,
    slug: str,
    is_active: bool = True,
    is_published: bool = True,
    catalog_order: int | None = None,
    supports_resume: bool = False,
    supports_uploads: bool = False,
    version_id: UUID | None = None,
    version_is_active: bool | None = True,
) -> UUID | None:
    db_session.add(
        LabModel(
            id=lab_id,
            slug=slug,
            name=f"Name for {slug}",
            summary=f"Summary for {slug}",
            is_active=is_active,
            is_published=is_published,
            catalog_order=catalog_order,
            supports_resume=supports_resume,
            supports_uploads=supports_uploads,
        )
    )
    if version_is_active is None:
        db_session.flush()
        return None

    resolved_version_id = version_id or uuid4()
    db_session.add(
        LabVersionModel(
            id=resolved_version_id,
            lab_id=lab_id,
            version="v1",
            is_active=version_is_active,
        )
    )
    db_session.flush()
    return resolved_version_id


@pytest.mark.usefixtures("engine")
def test_get_lab_catalog_returns_published_launchable_labs_in_order(
    db_session: Session,
) -> None:
    second_lab_id = uuid4()
    first_lab_id = uuid4()
    _add_lab(
        db_session,
        lab_id=second_lab_id,
        slug="second-lab",
        catalog_order=20,
        supports_uploads=True,
    )
    _add_lab(
        db_session,
        lab_id=first_lab_id,
        slug="first-lab",
        catalog_order=10,
        supports_resume=True,
    )
    _add_lab(
        db_session,
        lab_id=uuid4(),
        slug="unpublished-lab",
        is_published=False,
        catalog_order=0,
    )
    _add_lab(
        db_session,
        lab_id=uuid4(),
        slug="inactive-lab",
        is_active=False,
        catalog_order=0,
    )
    _add_lab(
        db_session,
        lab_id=uuid4(),
        slug="no-active-version",
        catalog_order=0,
        version_is_active=False,
    )
    _add_lab(
        db_session,
        lab_id=uuid4(),
        slug="unversioned-lab",
        catalog_order=0,
        version_is_active=None,
    )

    rows = SQLAlchemyLabRepository(db=db_session).get_lab_catalog()

    assert [row.lab_id for row in rows] == [first_lab_id, second_lab_id]
    assert rows[0].slug == "first-lab"
    assert rows[0].name == "Name for first-lab"
    assert rows[0].summary == "Summary for first-lab"
    assert rows[0].supports_resume is True
    assert rows[0].supports_uploads is False
    assert rows[1].supports_resume is False
    assert rows[1].supports_uploads is True


@pytest.mark.usefixtures("engine")
def test_validate_lab_requires_published_active_lab_and_version(
    db_session: Session,
) -> None:
    available_lab_id = uuid4()
    unpublished_lab_id = uuid4()
    inactive_lab_id = uuid4()
    inactive_version_lab_id = uuid4()
    unversioned_lab_id = uuid4()

    _add_lab(db_session, lab_id=available_lab_id, slug="available")
    _add_lab(
        db_session,
        lab_id=unpublished_lab_id,
        slug="unpublished",
        is_published=False,
    )
    _add_lab(
        db_session,
        lab_id=inactive_lab_id,
        slug="inactive",
        is_active=False,
    )
    _add_lab(
        db_session,
        lab_id=inactive_version_lab_id,
        slug="inactive-version",
        version_is_active=False,
    )
    _add_lab(
        db_session,
        lab_id=unversioned_lab_id,
        slug="unversioned",
        version_is_active=None,
    )

    repo = SQLAlchemyLabRepository(db=db_session)

    assert repo.validate_lab(available_lab_id) is True
    assert repo.validate_lab(unpublished_lab_id) is False
    assert repo.validate_lab(inactive_lab_id) is False
    assert repo.validate_lab(inactive_version_lab_id) is False
    assert repo.validate_lab(unversioned_lab_id) is False
    assert repo.validate_lab(uuid4()) is False


@pytest.mark.usefixtures("engine")
def test_get_active_version_id_fails_closed_for_unpublished_lab(
    db_session: Session,
) -> None:
    lab_id = uuid4()
    version_id = _add_lab(
        db_session,
        lab_id=lab_id,
        slug="unpublished",
        is_published=False,
    )
    assert version_id is not None

    repo = SQLAlchemyLabRepository(db=db_session)

    assert repo.get_active_version_id(lab_id) is None


@pytest.mark.usefixtures("engine")
def test_get_runtime_binding_returns_expected_lab3_mapping(db_session: Session) -> None:
    _add_lab(
        db_session,
        lab_id=LAB_3_ID,
        slug="memory-poisoning",
        version_id=LAB_3_VERSION_ID,
    )

    repo = SQLAlchemyLabRepository(db=db_session)
    binding = repo.get_runtime_binding(lab_id=LAB_3_ID, lab_version_id=LAB_3_VERSION_ID)

    assert binding.lab_slug == "memory-poisoning"
    assert binding.lab_version == "v1"
