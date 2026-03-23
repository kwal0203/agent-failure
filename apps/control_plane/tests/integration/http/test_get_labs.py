from collections.abc import Callable
from typing import cast
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.control_plane.src.application.common.types import GetLabCatalogRow
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.lab_repository import (
    SQLAlchemyLabRepository,
)
from apps.control_plane.src.interfaces.http.auth import Principal, get_current_principal
from apps.control_plane.src.interfaces.http.main import app


def _override_principal(user_id: UUID, role: str) -> Callable[[], Principal]:
    def _dependency_override() -> Principal:
        return Principal(user_id=user_id, role=role)

    return _dependency_override


def _override_db_session():
    def _dependency_override():
        try:
            yield cast(Session, None)
        finally:
            pass

    return _dependency_override


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_get_labs_returns_200_with_catalog() -> None:
    app.dependency_overrides[get_db_session] = _override_db_session()
    try:
        client = TestClient(app)
        response = client.get(
            "/api/v1/labs",
            headers=_auth_header(token="local:learner-user:learner"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert "labs" in body
    labs = body["labs"]
    assert isinstance(labs, list)
    assert len(labs) >= 1

    first = labs[0]
    assert "id" in first
    assert "slug" in first
    assert "name" in first
    assert "summary" in first
    assert "capabilities" in first
    assert "supports_resume" in first["capabilities"]
    assert "supports_uploads" in first["capabilities"]


def test_get_labs_returns_empty_catalog(monkeypatch) -> None:
    def _empty_catalog(self: SQLAlchemyLabRepository) -> list[GetLabCatalogRow]:
        return []

    app.dependency_overrides[get_db_session] = _override_db_session()
    try:
        monkeypatch.setattr(SQLAlchemyLabRepository, "get_lab_catalog", _empty_catalog)
        client = TestClient(app)
        response = client.get(
            "/api/v1/labs",
            headers=_auth_header(token="local:learner-user:learner"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["labs"] == []


def test_get_labs_returns_401_when_unauthenticated() -> None:
    app.dependency_overrides[get_db_session] = _override_db_session()
    try:
        client = TestClient(app)
        response = client.get(
            "/api/v1/labs",
            headers={"Authorization": "Token invalid"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHENTICATED"
    assert body["error"]["retryable"] is False


def test_get_labs_returns_403_for_forbidden_role() -> None:
    app.dependency_overrides[get_db_session] = _override_db_session()
    app.dependency_overrides[get_current_principal] = _override_principal(
        user_id=uuid4(), role="viewer"
    )
    try:
        client = TestClient(app)
        response = client.get("/api/v1/labs")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "FORBIDDEN"
    assert body["error"]["retryable"] is False
