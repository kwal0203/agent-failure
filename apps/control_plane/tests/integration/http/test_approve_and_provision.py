from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.control_plane.src.application.instructor_provisioning.types import (
    InstructorIdentityResult,
)
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.models import (
    ClassCodeModel,
    InstructorCourseMembershipModel,
    PilotRequestModel,
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
    def ensure_instructor_group_membership(
        self, *, email: str, create_user_if_missing: bool
    ) -> InstructorIdentityResult:
        return InstructorIdentityResult(
            email=email,
            user_created=create_user_if_missing,
            invite_sent=create_user_if_missing,
            group_assigned=True,
        )


class _FailingStubIdentityProvider:
    def ensure_instructor_group_membership(
        self, *, email: str, create_user_if_missing: bool
    ) -> InstructorIdentityResult:
        raise ValueError("identity provider unavailable")


class _CrashingStubIdentityProvider:
    def ensure_instructor_group_membership(
        self, *, email: str, create_user_if_missing: bool
    ) -> InstructorIdentityResult:
        _ = email, create_user_if_missing
        raise RuntimeError("botocore NoCredentialsError")


def test_approve_and_provision_happy_path(db_session: Session) -> None:
    row = PilotRequestModel(
        full_name="Instructor One",
        work_email="instructor@university.edu",
        university="Northwood University",
        status="contacted",
        course_name="CS447",
        cohort_size=120,
    )
    db_session.add(row)
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_instructor_identity_provider] = lambda: (
        _StubIdentityProvider()
    )
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/pilot-requests/{row.id}/approve-and-provision",
            headers=_auth_header("local:admin@example.edu:admin"),
            json={
                "courseId": "course-cs447-fall-2026",
                "courseName": "CS447 Fall 2026",
                "classCode": "CS447-FALL26",
                "instructorEmail": "instructor@university.edu",
                "classCodeMaxUses": 200,
                "createInstructorIfMissing": True,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["pilotRequest"]["status"] == "approved"
    assert body["approvedStep"] is True
    assert body["pilotProvisionStep"]["classCode"] == "CS447-FALL26"
    assert body["instructorProvisionStep"]["groupAssigned"] is True

    class_code = (
        db_session.query(ClassCodeModel)
        .filter(ClassCodeModel.code == "CS447-FALL26")
        .one_or_none()
    )
    assert class_code is not None

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


def test_approve_and_provision_requires_admin(db_session: Session) -> None:
    row = PilotRequestModel(
        full_name="Instructor One",
        work_email="instructor@university.edu",
        university="Northwood University",
        status="contacted",
    )
    db_session.add(row)
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_instructor_identity_provider] = lambda: (
        _StubIdentityProvider()
    )
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/pilot-requests/{row.id}/approve-and-provision",
            headers=_auth_header("local:staff@example.edu:staff"),
            json={
                "courseId": "course-cs447-fall-2026",
                "courseName": "CS447 Fall 2026",
                "classCode": "CS447-FALL26",
                "instructorEmail": "instructor@university.edu",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_approve_and_provision_sets_failed_status_on_instructor_error(
    db_session: Session,
) -> None:
    row = PilotRequestModel(
        full_name="Instructor One",
        work_email="instructor@university.edu",
        university="Northwood University",
        status="contacted",
        course_name="CS447",
        cohort_size=120,
    )
    db_session.add(row)
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_instructor_identity_provider] = lambda: (
        _FailingStubIdentityProvider()
    )
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/pilot-requests/{row.id}/approve-and-provision",
            headers=_auth_header("local:admin@example.edu:admin"),
            json={
                "courseId": "course-cs447-fall-2026",
                "courseName": "CS447 Fall 2026",
                "classCode": "CS447-FALL26",
                "instructorEmail": "instructor@university.edu",
                "classCodeMaxUses": 200,
                "createInstructorIfMissing": True,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["pilotRequest"]["status"] == "approved_provisioning_failed"
    assert body["approvedStep"] is True
    assert body["pilotProvisionStep"]["classCode"] == "CS447-FALL26"
    assert body["instructorProvisionStep"] is None
    assert body["instructorProvisionError"] == "identity provider unavailable"


def test_retry_approve_and_provision_from_failed_state(db_session: Session) -> None:
    row = PilotRequestModel(
        full_name="Instructor One",
        work_email="instructor@university.edu",
        university="Northwood University",
        status="approved_provisioning_failed",
        course_name="CS447",
        cohort_size=120,
    )
    db_session.add(row)
    db_session.flush()

    class_code = ClassCodeModel(
        code="CS447-FALL26",
        course_id="course-cs447-fall-2026",
        course_name="CS447 Fall 2026",
        status="active",
        max_uses=200,
    )
    db_session.add(class_code)
    db_session.commit()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_instructor_identity_provider] = lambda: (
        _StubIdentityProvider()
    )
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/pilot-requests/{row.id}/approve-and-provision",
            headers=_auth_header("local:admin@example.edu:admin"),
            json={
                "courseId": "course-cs447-fall-2026",
                "courseName": "CS447 Fall 2026",
                "classCode": "CS447-FALL26",
                "instructorEmail": "instructor@university.edu",
                "classCodeMaxUses": 200,
                "createInstructorIfMissing": True,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["pilotRequest"]["status"] == "approved"
    assert body["approvedStep"] is True
    assert body["pilotProvisionStep"]["classCode"] == "CS447-FALL26"
    assert body["instructorProvisionStep"]["groupAssigned"] is True


def test_approve_and_provision_sets_failed_status_on_unexpected_identity_error(
    db_session: Session,
) -> None:
    row = PilotRequestModel(
        full_name="Instructor One",
        work_email="instructor@university.edu",
        university="Northwood University",
        status="contacted",
        course_name="CS447",
        cohort_size=120,
    )
    db_session.add(row)
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_instructor_identity_provider] = lambda: (
        _CrashingStubIdentityProvider()
    )
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/pilot-requests/{row.id}/approve-and-provision",
            headers=_auth_header("local:admin@example.edu:admin"),
            json={
                "courseId": "course-cs447-fall-2026",
                "courseName": "CS447 Fall 2026",
                "classCode": "CS447-FALL26",
                "instructorEmail": "instructor@university.edu",
                "classCodeMaxUses": 200,
                "createInstructorIfMissing": True,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["pilotRequest"]["status"] == "approved_provisioning_failed"
    assert body["instructorProvisionStep"] is None
    assert (
        body["instructorProvisionError"] == "Failed to provision instructor identity."
    )
