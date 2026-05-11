from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.models import (
    ClassCodeModel,
    EnrollmentModel,
    EnrollmentTokenModel,
)
from apps.control_plane.src.interfaces.http.auth import get_current_principal
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


def _seed_class_code(
    db_session: Session,
    *,
    code: str = "ABC123",
    status: str = "active",
    expires_at: datetime | None = None,
    max_uses: int | None = None,
    uses: int = 0,
) -> None:
    db_session.add(
        ClassCodeModel(
            code=code,
            course_id="course_01",
            course_name="CS 447 - AI Agent Security",
            status=status,
            expires_at=expires_at,
            max_uses=max_uses,
            uses=uses,
        )
    )
    db_session.flush()


def test_validate_class_code_returns_token_and_course(db_session: Session) -> None:
    _seed_class_code(db_session, code="ABC123")

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/enrollment/validate-class-code",
            json={"classCode": "ABC123", "email": "student@example.edu"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert isinstance(body["enrollmentToken"], str)
    assert body["expiresInSeconds"] >= 60
    assert body["course"] == {
        "id": "course_01",
        "name": "CS 447 - AI Agent Security",
    }
    assert body["error"] is None


def test_validate_class_code_rejects_expired_or_maxed_code(db_session: Session) -> None:
    _seed_class_code(
        db_session,
        code="EXPIRED",
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    _seed_class_code(db_session, code="MAXED", max_uses=1, uses=1)

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        expired_response = client.post(
            "/api/v1/enrollment/validate-class-code",
            json={"classCode": "EXPIRED", "email": "student@example.edu"},
        )
        maxed_response = client.post(
            "/api/v1/enrollment/validate-class-code",
            json={"classCode": "MAXED", "email": "student@example.edu"},
        )
    finally:
        app.dependency_overrides.clear()

    assert expired_response.status_code == 200
    assert expired_response.json() == {
        "valid": False,
        "enrollmentToken": None,
        "expiresInSeconds": None,
        "course": None,
        "error": "Invalid or expired class code",
    }

    assert maxed_response.status_code == 200
    assert maxed_response.json() == {
        "valid": False,
        "enrollmentToken": None,
        "expiresInSeconds": None,
        "course": None,
        "error": "Class code usage limit reached",
    }


def test_redeem_enrollment_creates_enrollment(db_session: Session) -> None:
    _seed_class_code(db_session, code="ABC123")

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        validate = client.post(
            "/api/v1/enrollment/validate-class-code",
            json={"classCode": "ABC123", "email": "student@example.edu"},
        )
        token = validate.json()["enrollmentToken"]

        response = client.post(
            "/api/v1/enrollment/redeem",
            headers=_auth_header("local:student@example.edu:learner"),
            json={"enrollmentToken": token},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "enrolled": True,
        "course": {"id": "course_01", "name": "CS 447 - AI Agent Security"},
        "error": None,
    }

    enrollment_count = db_session.query(EnrollmentModel).count()
    token_rows = db_session.query(EnrollmentTokenModel).all()
    assert enrollment_count == 1
    assert len(token_rows) == 1
    assert token_rows[0].redeemed_at is not None


def test_redeem_rejects_email_mismatch(db_session: Session) -> None:
    _seed_class_code(db_session, code="ABC123")

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        validate = client.post(
            "/api/v1/enrollment/validate-class-code",
            json={"classCode": "ABC123", "email": "student@example.edu"},
        )
        token = validate.json()["enrollmentToken"]

        response = client.post(
            "/api/v1/enrollment/redeem",
            headers=_auth_header("local:other@example.edu:learner"),
            json={"enrollmentToken": token},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "enrolled": False,
        "course": None,
        "error": "Enrollment token email does not match authenticated user",
    }


def test_redeem_is_idempotent_for_already_enrolled_user(db_session: Session) -> None:
    _seed_class_code(db_session, code="ABC123")

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        validate = client.post(
            "/api/v1/enrollment/validate-class-code",
            json={"classCode": "ABC123", "email": "student@example.edu"},
        )
        token = validate.json()["enrollmentToken"]

        first = client.post(
            "/api/v1/enrollment/redeem",
            headers=_auth_header("local:student@example.edu:learner"),
            json={"enrollmentToken": token},
        )
        second = client.post(
            "/api/v1/enrollment/redeem",
            headers=_auth_header("local:student@example.edu:learner"),
            json={"enrollmentToken": token},
        )
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["enrolled"] is True
    assert second.json() == {
        "enrolled": True,
        "course": {"id": "course_01", "name": "CS 447 - AI Agent Security"},
        "error": None,
    }
    assert db_session.query(EnrollmentModel).count() == 1


def test_redeem_rejects_expired_token(db_session: Session) -> None:
    _seed_class_code(db_session, code="ABC123")

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        validate = client.post(
            "/api/v1/enrollment/validate-class-code",
            json={"classCode": "ABC123", "email": "student@example.edu"},
        )
        token = validate.json()["enrollmentToken"]

        token_row = db_session.query(EnrollmentTokenModel).one()
        token_row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db_session.flush()

        response = client.post(
            "/api/v1/enrollment/redeem",
            headers=_auth_header("local:student@example.edu:learner"),
            json={"enrollmentToken": token},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "enrolled": False,
        "course": None,
        "error": "Token expired or already redeemed",
    }


def test_redeem_succeeds_when_principal_email_missing(db_session: Session) -> None:
    _seed_class_code(db_session, code="ABC123")

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_current_principal] = lambda: PrincipalContext(
        user_id=uuid4(),
        role="learner",
        email=None,
    )
    try:
        client = TestClient(app)
        validate = client.post(
            "/api/v1/enrollment/validate-class-code",
            json={"classCode": "ABC123", "email": "student@example.edu"},
        )
        token = validate.json()["enrollmentToken"]

        response = client.post(
            "/api/v1/enrollment/redeem",
            json={"enrollmentToken": token},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "enrolled": True,
        "course": {"id": "course_01", "name": "CS 447 - AI Agent Security"},
        "error": None,
    }
