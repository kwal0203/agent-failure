from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.control_plane.src.application.pilot_requests.notifications import (
    PilotRequestNotification,
)
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.models import PilotRequestModel
from apps.control_plane.src.interfaces.http.dependencies import (
    get_pilot_request_notifier,
)
from apps.control_plane.src.interfaces.http.main import app


def _override_db_session(db_session: Session):
    def _dependency_override():
        try:
            yield db_session
        finally:
            pass

    return _dependency_override


def _payload() -> dict[str, object]:
    return {
        "fullName": "Instructor One",
        "workEmail": "instructor@university.edu",
        "university": "Northwood University",
        "role": "Lecturer",
        "courseName": "CS447",
        "cohortSize": 120,
        "notes": "Pilot request for Fall term.",
    }


def test_create_pilot_request_happy_path(db_session: Session) -> None:
    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post("/api/v1/pilot-requests", json=_payload())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["requestId"], str)
    assert body["status"] == "new"
    assert isinstance(body["createdAt"], str)
    assert db_session.query(PilotRequestModel).count() == 1


def test_create_pilot_request_triggers_notification(db_session: Session) -> None:
    sent: list[PilotRequestNotification] = []

    class _SpyNotifier:
        def notify(self, payload: PilotRequestNotification) -> None:
            sent.append(payload)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_pilot_request_notifier] = lambda: _SpyNotifier()
    try:
        client = TestClient(app)
        response = client.post("/api/v1/pilot-requests", json=_payload())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert len(sent) == 1
    assert sent[0].work_email == "instructor@university.edu"


def test_create_pilot_request_validation_error(db_session: Session) -> None:
    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/pilot-requests",
            json={
                "fullName": "",
                "workEmail": "instructor@university.edu",
                "university": "",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_create_pilot_request_rejects_recent_duplicate(db_session: Session) -> None:
    db_session.add(
        PilotRequestModel(
            full_name="Instructor One",
            work_email="instructor@university.edu",
            university="Northwood University",
            status="new",
        )
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post("/api/v1/pilot-requests", json=_payload())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_create_pilot_request_rate_limited_by_email(db_session: Session) -> None:
    now = datetime.now(UTC)
    for _ in range(3):
        db_session.add(
            PilotRequestModel(
                full_name="Instructor One",
                work_email="instructor@university.edu",
                university="Other University",
                status="new",
                created_at=now - timedelta(minutes=10),
            )
        )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post("/api/v1/pilot-requests", json=_payload())
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 429
    assert "Too many requests" in response.json()["detail"]
