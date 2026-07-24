from uuid import uuid4, uuid4 as _uuid4

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.control_plane.src.infrastructure.config.settings import AdmissionSettings
from apps.control_plane.src.infrastructure.persistence.db import (
    SessionFactory,
    get_db_session,
)
from apps.control_plane.src.infrastructure.persistence.models import (
    LabModel,
    LabVersionModel,
    SessionModel,
)
from apps.control_plane.src.infrastructure.policy.admission_policy import (
    ConcreteAdmissionPolicy,
)
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.dependencies import (
    get_admission_policy,
    get_create_session_uow,
)
from apps.control_plane.src.interfaces.http.main import app
from apps.control_plane.src.infrastructure.persistence.unit_of_work_create_session import (
    SQLAlchemyCreateSessionUnitOfWork,
)


def _override_principal(user_id, role):
    def _dependency_override() -> PrincipalContext:
        return PrincipalContext(user_id=user_id, role=role)

    return _dependency_override


def _override_create_session_uow() -> SQLAlchemyCreateSessionUnitOfWork:
    return SQLAlchemyCreateSessionUnitOfWork(session_factory=SessionFactory)


def _seed_lab_with_active_version(*, lab_id):
    lab_version_id = _uuid4()
    with SessionFactory() as db:
        db.add(
            LabModel(
                id=lab_id,
                slug=f"lab-{str(lab_id)[:8]}",
                name="Test Lab",
                summary="test",
                is_active=True,
                is_published=True,
            )
        )
        db.add(
            LabVersionModel(
                id=lab_version_id,
                lab_id=lab_id,
                version="v1",
                is_active=True,
            )
        )
        db.commit()
    return lab_version_id


def _create_sessions_for_user(*, owner_user_id, count, lab_id):
    with SessionFactory() as db:
        for _ in range(count):
            db.add(
                SessionModel(
                    lab_id=lab_id,
                    owner_user_id=owner_user_id,
                    state="ACTIVE",
                    last_transition_actor="system",
                    lab_difficulty="medium",
                )
            )
        db.commit()


def _make_admission_override(max_per_user=3, max_global=20):
    def _override(db: Session = Depends(get_db_session)):
        return ConcreteAdmissionPolicy(
            db=db,
            settings=AdmissionSettings(
                max_sessions_per_user=max_per_user,
                max_sessions_global=max_global,
            ),
        )

    return _override


@pytest.mark.usefixtures("engine")
def test_create_session_rejected_when_user_quota_exceeded() -> None:
    principal_id = uuid4()
    lab_id = uuid4()
    _seed_lab_with_active_version(lab_id=lab_id)

    _create_sessions_for_user(owner_user_id=principal_id, count=3, lab_id=lab_id)

    app.dependency_overrides[get_current_principal] = _override_principal(
        user_id=principal_id, role="learner"
    )
    app.dependency_overrides[get_create_session_uow] = _override_create_session_uow
    app.dependency_overrides[get_admission_policy] = _make_admission_override(
        max_per_user=3
    )
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/sessions",
            headers={"Idempotency-Key": "quota-exceeded-1"},
            json={"lab_id": str(lab_id)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 429
    body = response.json()
    assert body["error"]["code"] == "QUOTA_EXCEEDED"
    assert body["error"]["details"]["current"] == 3
    assert body["error"]["details"]["quota"] == 3


@pytest.mark.usefixtures("engine")
def test_create_session_allowed_when_under_user_quota() -> None:
    principal_id = uuid4()
    lab_id = uuid4()
    _seed_lab_with_active_version(lab_id=lab_id)

    _create_sessions_for_user(owner_user_id=principal_id, count=2, lab_id=lab_id)

    app.dependency_overrides[get_current_principal] = _override_principal(
        user_id=principal_id, role="learner"
    )
    app.dependency_overrides[get_create_session_uow] = _override_create_session_uow
    app.dependency_overrides[get_admission_policy] = _make_admission_override(
        max_per_user=3
    )
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/sessions",
            headers={"Idempotency-Key": "quota-ok-1"},
            json={"lab_id": str(lab_id)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202


@pytest.mark.usefixtures("engine")
def test_create_session_rejected_when_global_capacity_exceeded() -> None:
    principal_id = uuid4()
    other_user_id = uuid4()
    lab_id = uuid4()
    _seed_lab_with_active_version(lab_id=lab_id)

    _create_sessions_for_user(owner_user_id=other_user_id, count=20, lab_id=lab_id)

    app.dependency_overrides[get_current_principal] = _override_principal(
        user_id=principal_id, role="learner"
    )
    app.dependency_overrides[get_create_session_uow] = _override_create_session_uow
    app.dependency_overrides[get_admission_policy] = _make_admission_override(
        max_per_user=100, max_global=20
    )
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/sessions",
            headers={"Idempotency-Key": "global-cap-1"},
            json={"lab_id": str(lab_id)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 429
    body = response.json()
    assert body["error"]["code"] == "RATE_LIMITED"
    assert body["error"]["details"]["current"] == 20
    assert body["error"]["details"]["limit"] == 20


@pytest.mark.usefixtures("engine")
def test_create_session_does_not_count_terminal_sessions() -> None:
    principal_id = uuid4()
    lab_id = uuid4()
    _seed_lab_with_active_version(lab_id=lab_id)

    with SessionFactory() as db:
        for state in ("COMPLETED", "FAILED", "EXPIRED"):
            db.add(
                SessionModel(
                    lab_id=lab_id,
                    owner_user_id=principal_id,
                    state=state,
                    last_transition_actor="system",
                    lab_difficulty="medium",
                )
            )
        db.commit()

    app.dependency_overrides[get_current_principal] = _override_principal(
        user_id=principal_id, role="learner"
    )
    app.dependency_overrides[get_create_session_uow] = _override_create_session_uow
    app.dependency_overrides[get_admission_policy] = _make_admission_override(
        max_per_user=1
    )
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/sessions",
            headers={"Idempotency-Key": "terminal-ok-1"},
            json={"lab_id": str(lab_id)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
