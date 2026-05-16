from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.models import (
    ClassCodeModel,
    PilotRequestModel,
)
from apps.control_plane.src.interfaces.http.main import app


def _override_db_session(db_session: Session):
    def _dependency_override():
        try:
            yield db_session
        finally:
            pass

    return _dependency_override


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _payload() -> dict[str, object]:
    return {
        "courseId": "course-cs447-fall-2026",
        "courseName": "CS447 Fall 2026",
        "classCode": "CS447-FALL26",
        "instructorEmail": "instructor@university.edu",
        "maxUses": 250,
    }


def test_provision_pilot_request_requires_admin(db_session: Session) -> None:
    row = PilotRequestModel(
        full_name="Instructor One",
        work_email="instructor@university.edu",
        university="Northwood University",
        status="contacted",
    )
    db_session.add(row)
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/pilot-requests/{row.id}/provision",
            headers=_auth_header("local:learner@example.edu:learner"),
            json=_payload(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_provision_pilot_request_creates_class_code_and_summary(
    db_session: Session,
) -> None:
    row = PilotRequestModel(
        full_name="Instructor One",
        work_email="instructor@university.edu",
        university="Northwood University",
        status="contacted",
    )
    db_session.add(row)
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/pilot-requests/{row.id}/provision",
            headers=_auth_header("local:admin@example.edu:admin"),
            json=_payload(),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["created"] is True
    assert body["provisioningSummary"]["pilotRequestId"] == str(row.id)
    assert body["provisioningSummary"]["classCode"] == "CS447-FALL26"
    assert body["provisioningSummary"]["classCodeStatus"] == "active"

    class_code = (
        db_session.query(ClassCodeModel)
        .filter(ClassCodeModel.code == "CS447-FALL26")
        .one_or_none()
    )
    assert class_code is not None
    assert class_code.course_id == "course-cs447-fall-2026"


def test_provision_pilot_request_is_idempotent(db_session: Session) -> None:
    row = PilotRequestModel(
        full_name="Instructor One",
        work_email="instructor@university.edu",
        university="Northwood University",
        status="contacted",
    )
    db_session.add(row)
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        first = client.post(
            f"/api/v1/pilot-requests/{row.id}/provision",
            headers=_auth_header("local:admin@example.edu:admin"),
            json=_payload(),
        )
        second = client.post(
            f"/api/v1/pilot-requests/{row.id}/provision",
            headers=_auth_header("local:admin@example.edu:admin"),
            json=_payload(),
        )
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["created"] is True
    assert second.json()["created"] is False
