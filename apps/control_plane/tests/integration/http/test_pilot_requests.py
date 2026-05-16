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


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


def test_list_pilot_requests_requires_admin_or_staff(db_session: Session) -> None:
    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            "/api/v1/pilot-requests",
            headers=_auth_header("local:learner@example.edu:learner"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_list_pilot_requests_with_filters_and_pagination(db_session: Session) -> None:
    now = datetime.now(UTC)
    db_session.add(
        PilotRequestModel(
            full_name="One",
            work_email="one@example.edu",
            university="U1",
            status="new",
            created_at=now - timedelta(days=3),
        )
    )
    db_session.add(
        PilotRequestModel(
            full_name="Two",
            work_email="two@example.edu",
            university="U2",
            status="contacted",
            created_at=now - timedelta(days=2),
        )
    )
    db_session.add(
        PilotRequestModel(
            full_name="Three",
            work_email="three@example.edu",
            university="U3",
            status="new",
            created_at=now - timedelta(days=1),
        )
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            "/api/v1/pilot-requests",
            headers=_auth_header("local:admin@example.edu:admin"),
            params={"status": "new", "limit": 1, "offset": 0},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["limit"] == 1
    assert body["offset"] == 0
    assert len(body["items"]) == 1
    assert body["items"][0]["status"] == "new"


def test_list_pilot_requests_created_after_filter(db_session: Session) -> None:
    now = datetime.now(UTC)
    old_row = PilotRequestModel(
        full_name="Old",
        work_email="old@example.edu",
        university="U1",
        status="new",
        created_at=now - timedelta(days=10),
    )
    new_row = PilotRequestModel(
        full_name="New",
        work_email="new@example.edu",
        university="U1",
        status="new",
        created_at=now - timedelta(days=1),
    )
    db_session.add(old_row)
    db_session.add(new_row)
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            "/api/v1/pilot-requests",
            headers=_auth_header("local:admin@example.edu:admin"),
            params={"created_after": (now - timedelta(days=2)).isoformat()},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["workEmail"] == "new@example.edu"
