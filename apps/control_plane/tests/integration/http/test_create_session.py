from collections.abc import Callable
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.models import (
    IdempotencyRecordModel,
    LabModel,
    LabVersionModel,
    OutboxEventModel,
    SessionModel,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work_create_session import (
    SQLAlchemyCreateSessionUnitOfWork,
)
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.dependencies import get_create_session_uow
from apps.control_plane.src.interfaces.http.main import app

LAB_3_ID = UUID("33333333-3333-3333-3333-333333333333")
LAB_3_VERSION_ID = UUID("33333333-3333-3333-3333-aaaaaaaaaaa3")


def _override_principal(user_id: UUID, role: str) -> Callable[[], PrincipalContext]:
    def _dependency_override() -> PrincipalContext:
        return PrincipalContext(user_id=user_id, role=role)

    return _dependency_override


def _override_create_session_uow() -> SQLAlchemyCreateSessionUnitOfWork:
    return SQLAlchemyCreateSessionUnitOfWork(session_factory=SessionFactory)


def _seed_lab_with_active_version(*, lab_id: UUID) -> UUID:
    lab_version_id = uuid4()
    with SessionFactory() as db:
        db.add(
            LabModel(
                id=lab_id,
                slug=f"lab-{str(lab_id)[:8]}",
                name="Test Lab",
                summary="test",
                is_active=True,
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


@pytest.mark.usefixtures("engine")
def test_create_session_returns_202() -> None:
    principal_id = uuid4()
    lab_id = uuid4()
    _seed_lab_with_active_version(lab_id=lab_id)
    key = "create-session-key-1"

    app.dependency_overrides[get_current_principal] = _override_principal(
        user_id=principal_id, role="learner"
    )
    app.dependency_overrides[get_create_session_uow] = _override_create_session_uow
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/sessions",
            headers={"Idempotency-Key": key},
            json={"lab_id": str(lab_id)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    body = response.json()
    assert body["session"]["lab_id"] == str(lab_id)
    assert body["session"]["lab_difficulty"] == "medium"
    assert body["session"]["state"] == "PROVISIONING"
    assert body["session"]["resume_mode"] == "hot_resume"
    assert body["session"]["created_at"] is not None

    session_id = body["session"]["id"]
    with SessionFactory() as verify_db:
        session_count = verify_db.execute(
            select(func.count()).select_from(SessionModel)
        ).scalar_one()
        assert session_count == 1

        idempo_count = verify_db.execute(
            select(func.count())
            .select_from(IdempotencyRecordModel)
            .where(
                IdempotencyRecordModel.operation == "create_session",
                IdempotencyRecordModel.idempotency_key == key,
            )
        ).scalar_one()
        assert idempo_count == 1

        outbox_count = verify_db.execute(
            select(func.count())
            .select_from(OutboxEventModel)
            .where(
                OutboxEventModel.event_type == "session.provisioning.v1",
                OutboxEventModel.aggregate_id == UUID(session_id),
            )
        ).scalar_one()
        assert outbox_count == 1

        session_row = verify_db.execute(
            select(SessionModel).where(SessionModel.id == UUID(session_id))
        ).scalar_one()
        assert session_row.completion_status == "in_progress"
        assert session_row.completed_at is None
        assert session_row.completion_reason_code is None

        outbox_event = verify_db.execute(
            select(OutboxEventModel).where(
                OutboxEventModel.event_type == "session.provisioning.v1",
                OutboxEventModel.aggregate_id == UUID(session_id),
            )
        ).scalar_one()
        assert outbox_event.payload["lab_difficulty"] == "medium"


@pytest.mark.usefixtures("engine")
def test_create_session_accepts_explicit_lab_difficulty_easy() -> None:
    principal_id = uuid4()
    lab_id = uuid4()
    _seed_lab_with_active_version(lab_id=lab_id)
    key = "create-session-key-easy"

    app.dependency_overrides[get_current_principal] = _override_principal(
        user_id=principal_id, role="learner"
    )
    app.dependency_overrides[get_create_session_uow] = _override_create_session_uow
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/sessions",
            headers={"Idempotency-Key": key},
            json={"lab_id": str(lab_id), "lab_difficulty": "easy"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    body = response.json()
    assert body["session"]["lab_difficulty"] == "easy"

    session_id = body["session"]["id"]
    with SessionFactory() as verify_db:
        outbox_event = verify_db.execute(
            select(OutboxEventModel).where(
                OutboxEventModel.event_type == "session.provisioning.v1",
                OutboxEventModel.aggregate_id == UUID(session_id),
            )
        ).scalar_one()
        assert outbox_event.payload["lab_difficulty"] == "easy"


@pytest.mark.usefixtures("engine")
def test_create_session_rejects_invalid_lab_difficulty() -> None:
    principal_id = uuid4()
    lab_id = uuid4()
    _seed_lab_with_active_version(lab_id=lab_id)
    key = "create-session-key-invalid-difficulty"

    app.dependency_overrides[get_current_principal] = _override_principal(
        user_id=principal_id, role="learner"
    )
    app.dependency_overrides[get_create_session_uow] = _override_create_session_uow
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/sessions",
            headers={"Idempotency-Key": key},
            json={"lab_id": str(lab_id), "lab_difficulty": "hard"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_LAB_DIFFICULTY"
    assert body["error"]["retryable"] is False


@pytest.mark.usefixtures("engine")
def test_create_session_replay_same_key_returns_existing_session() -> None:
    principal_id = uuid4()
    lab_id = uuid4()
    _seed_lab_with_active_version(lab_id=lab_id)
    key = "create-session-key-2"

    app.dependency_overrides[get_current_principal] = _override_principal(
        user_id=principal_id, role="learner"
    )
    app.dependency_overrides[get_create_session_uow] = _override_create_session_uow
    try:
        client = TestClient(app)
        first = client.post(
            "/api/v1/sessions",
            headers={"Idempotency-Key": key},
            json={"lab_id": str(lab_id)},
        )
        second = client.post(
            "/api/v1/sessions",
            headers={"Idempotency-Key": key},
            json={"lab_id": str(lab_id)},
        )
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["session"]["id"] == first.json()["session"]["id"]

    with SessionFactory() as verify_db:
        session_count = verify_db.execute(
            select(func.count()).select_from(SessionModel)
        ).scalar_one()
        assert session_count == 1

        idempo_count = verify_db.execute(
            select(func.count())
            .select_from(IdempotencyRecordModel)
            .where(
                IdempotencyRecordModel.operation == "create_session",
                IdempotencyRecordModel.idempotency_key == key,
            )
        ).scalar_one()
        assert idempo_count == 1

        outbox_count = verify_db.execute(
            select(func.count()).select_from(OutboxEventModel)
        ).scalar_one()
        assert outbox_count == 1


@pytest.mark.usefixtures("engine")
def test_create_session_lab3_uses_db_active_lab_version() -> None:
    principal_id = uuid4()
    key = "create-session-key-lab3"

    with SessionFactory() as db:
        db.add(
            LabModel(
                id=LAB_3_ID,
                slug="memory-poisoning",
                name="Memory Poisoning",
                summary="test",
                is_active=True,
            )
        )
        db.add(
            LabVersionModel(
                id=LAB_3_VERSION_ID,
                lab_id=LAB_3_ID,
                version="v1",
                is_active=True,
            )
        )
        db.commit()

    app.dependency_overrides[get_current_principal] = _override_principal(
        user_id=principal_id, role="learner"
    )
    app.dependency_overrides[get_create_session_uow] = _override_create_session_uow
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/sessions",
            headers={"Idempotency-Key": key},
            json={"lab_id": str(LAB_3_ID)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    session_id = UUID(response.json()["session"]["id"])

    with SessionFactory() as db:
        session = db.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        ).scalar_one()
        assert session.lab_version_id == LAB_3_VERSION_ID


@pytest.mark.usefixtures("engine")
def test_create_session_invalid_idempotency_key_returns_typed_error() -> None:
    principal_id = uuid4()
    lab_id = uuid4()
    _seed_lab_with_active_version(lab_id=lab_id)

    app.dependency_overrides[get_current_principal] = _override_principal(
        user_id=principal_id, role="learner"
    )
    app.dependency_overrides[get_create_session_uow] = _override_create_session_uow
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/sessions",
            headers={"Idempotency-Key": "   "},
            json={"lab_id": str(lab_id)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "INVALID_IDEMPOTENCY_KEY"
    assert body["error"]["retryable"] is False


@pytest.mark.usefixtures("engine")
def test_create_session_lab_unavailable_returns_typed_error() -> None:
    principal_id = uuid4()
    lab_id = uuid4()
    key = "create-session-key-3"

    app.dependency_overrides[get_current_principal] = _override_principal(
        user_id=principal_id, role="learner"
    )
    app.dependency_overrides[get_create_session_uow] = _override_create_session_uow
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/sessions",
            headers={"Idempotency-Key": key},
            json={"lab_id": str(lab_id)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "LAB_NOT_AVAILABLE"
    assert body["error"]["retryable"] is False
    assert body["error"]["details"]["lab_id"] == str(lab_id)


@pytest.mark.usefixtures("engine")
def test_create_session_forbidden_returns_typed_error() -> None:
    principal_id = uuid4()
    lab_id = uuid4()
    _seed_lab_with_active_version(lab_id=lab_id)
    key = "create-session-key-4"

    app.dependency_overrides[get_current_principal] = _override_principal(
        user_id=principal_id, role="viewer"
    )
    app.dependency_overrides[get_create_session_uow] = _override_create_session_uow
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/sessions",
            headers={"Idempotency-Key": key},
            json={"lab_id": str(lab_id)},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "FORBIDDEN"
    assert body["error"]["retryable"] is False
    assert body["error"]["details"]["role"] == "viewer"
