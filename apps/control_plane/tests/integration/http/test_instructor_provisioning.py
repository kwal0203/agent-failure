from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import UUID

from apps.control_plane.src.application.instructor_provisioning.types import (
    InstructorIdentityResult,
)
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.models import (
    ClassCodeModel,
    InstructorCourseMembershipModel,
    PilotRequestModel,
    PilotRequestProvisionModel,
)
from apps.control_plane.src.interfaces.http.dependencies import (
    get_instructor_identity_provider,
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


class _StubIdentityProvider:
    def __init__(self) -> None:
        self.calls = 0

    def ensure_instructor_group_membership(
        self, *, email: str, create_user_if_missing: bool
    ) -> InstructorIdentityResult:
        self.calls += 1
        return InstructorIdentityResult(
            email=email,
            user_created=create_user_if_missing,
            invite_sent=create_user_if_missing,
            group_assigned=True,
        )


def _payload() -> dict[str, object]:
    return {
        "pilotRequestId": "",
        "instructorEmail": "instructor@university.edu",
        "createUserIfMissing": True,
    }


def _seed_pilot_provision_context(db_session: Session, pilot_request_id: UUID) -> None:
    class_code = ClassCodeModel(
        code="CS447-FALL26",
        course_id="course-cs447-fall-2026",
        course_name="CS447 Fall 2026",
        status="active",
        max_uses=200,
    )
    db_session.add(class_code)
    db_session.flush()
    db_session.add(
        PilotRequestProvisionModel(
            pilot_request_id=pilot_request_id,
            course_id="course-cs447-fall-2026",
            course_name="CS447 Fall 2026",
            class_code="CS447-FALL26",
            class_code_id=class_code.id,
            instructor_email="instructor@university.edu",
        )
    )
    db_session.flush()


def test_provision_instructor_requires_admin(db_session: Session) -> None:
    pilot_request = PilotRequestModel(
        full_name="Instructor One",
        work_email="instructor@university.edu",
        university="Northwood University",
        status="approved",
    )
    db_session.add(pilot_request)
    db_session.flush()
    _seed_pilot_provision_context(db_session, pilot_request.id)

    payload = _payload()
    payload["pilotRequestId"] = str(pilot_request.id)
    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_instructor_identity_provider] = lambda: (
        _StubIdentityProvider()
    )
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/admin/instructors/provision",
            headers=_auth_header("local:learner@example.edu:learner"),
            json=payload,
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_provision_instructor_happy_path(db_session: Session) -> None:
    pilot_request = PilotRequestModel(
        full_name="Instructor One",
        work_email="instructor@university.edu",
        university="Northwood University",
        status="approved",
    )
    db_session.add(pilot_request)
    db_session.flush()
    _seed_pilot_provision_context(db_session, pilot_request.id)

    payload = _payload()
    payload["pilotRequestId"] = str(pilot_request.id)
    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_instructor_identity_provider] = lambda: (
        _StubIdentityProvider()
    )
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/admin/instructors/provision",
            headers=_auth_header("local:admin@example.edu:admin"),
            json=payload,
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["provisioningSummary"]["courseId"] == "course-cs447-fall-2026"
    assert body["provisioningSummary"]["groupAssigned"] is True
    assert body["provisioningSummary"]["membershipCreated"] is True

    membership = (
        db_session.query(InstructorCourseMembershipModel)
        .filter(
            InstructorCourseMembershipModel.instructor_email
            == "instructor@university.edu",
            InstructorCourseMembershipModel.course_id == "course-cs447-fall-2026",
        )
        .one_or_none()
    )
    assert membership is not None


def test_provision_instructor_idempotent_membership(db_session: Session) -> None:
    pilot_request = PilotRequestModel(
        full_name="Instructor One",
        work_email="instructor@university.edu",
        university="Northwood University",
        status="approved",
    )
    db_session.add(pilot_request)
    db_session.flush()
    _seed_pilot_provision_context(db_session, pilot_request.id)

    payload = _payload()
    payload["pilotRequestId"] = str(pilot_request.id)
    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_instructor_identity_provider] = lambda: (
        _StubIdentityProvider()
    )
    try:
        client = TestClient(app)
        first = client.post(
            "/api/v1/admin/instructors/provision",
            headers=_auth_header("local:admin@example.edu:admin"),
            json=payload,
        )
        second = client.post(
            "/api/v1/admin/instructors/provision",
            headers=_auth_header("local:admin@example.edu:admin"),
            json=payload,
        )
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["provisioningSummary"]["membershipCreated"] is True
    assert second.json()["provisioningSummary"]["membershipCreated"] is False
