from collections.abc import Callable
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.models import (
    IdempotencyRecordModel,
    OutboxEventModel,
    SessionModel,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work_create_session import (
    SQLAlchemyCreateSessionUnitOfWork,
)
from apps.control_plane.src.infrastructure.persistence.lab_repository import (
    PostgresLabRepository,
)
from apps.control_plane.src.interfaces.http.auth import Principal, get_current_principal
from apps.control_plane.src.interfaces.http.dependencies import get_create_session_uow
from apps.control_plane.src.interfaces.http.main import app


def _override_principal(user_id: UUID, role: str) -> Callable[[], Principal]:
    def _dependency_override() -> Principal:
        return Principal(user_id=user_id, role=role)

    return _dependency_override


def _override_create_session_uow() -> SQLAlchemyCreateSessionUnitOfWork:
    return SQLAlchemyCreateSessionUnitOfWork(session_factory=SessionFactory)


@pytest.mark.usefixtures("engine")
def test_create_session_returns_202() -> None:
    principal_id = uuid4()
    lab_id = uuid4()
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


@pytest.mark.usefixtures("engine")
def test_create_session_replay_same_key_returns_existing_session() -> None:
    principal_id = uuid4()
    lab_id = uuid4()
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
def test_create_session_invalid_idempotency_key_returns_typed_error() -> None:
    principal_id = uuid4()
    lab_id = uuid4()

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
def test_create_session_lab_unavailable_returns_typed_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    principal_id = uuid4()
    lab_id = uuid4()
    key = "create-session-key-3"

    def _always_unavailable(self: PostgresLabRepository, lab_id: UUID) -> bool:
        _ = lab_id
        return False

    monkeypatch.setattr(PostgresLabRepository, "validate_lab", _always_unavailable)

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
