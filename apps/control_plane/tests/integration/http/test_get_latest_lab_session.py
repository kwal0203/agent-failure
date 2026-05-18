from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.models import SessionModel
from apps.control_plane.src.interfaces.http.main import app


def _override_db_session(db_session: Session):
    def _dependency_override():
        try:
            yield db_session
        finally:
            pass

    return _dependency_override


def _owner_user_id(username: str) -> UUID:
    return uuid5(namespace=NAMESPACE_URL, name=f"local-user:{username}")


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_session(
    db_session: Session,
    *,
    session_id: UUID,
    lab_id: UUID,
    owner_username: str,
    created_at: datetime,
) -> None:
    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=lab_id,
            lab_version_id=uuid4(),
            owner_user_id=_owner_user_id(owner_username),
            state="ACTIVE",
            last_transition_actor="seed",
            last_transition_reason=None,
            created_at=created_at,
        )
    )
    db_session.flush()


def test_get_latest_lab_session_returns_latest_for_owner(db_session: Session) -> None:
    owner_username = "learner-latest"
    other_username = "another-learner"
    lab_id = uuid4()
    now = datetime.now(timezone.utc)

    oldest_owner = uuid4()
    latest_owner = uuid4()
    other_user_newer = uuid4()
    _seed_session(
        db_session,
        session_id=oldest_owner,
        lab_id=lab_id,
        owner_username=owner_username,
        created_at=now - timedelta(minutes=3),
    )
    _seed_session(
        db_session,
        session_id=latest_owner,
        lab_id=lab_id,
        owner_username=owner_username,
        created_at=now - timedelta(minutes=1),
    )
    _seed_session(
        db_session,
        session_id=other_user_newer,
        lab_id=lab_id,
        owner_username=other_username,
        created_at=now,
    )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/labs/{lab_id}/latest-session",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["session_id"] == str(latest_owner)


def test_get_latest_lab_session_admin_can_see_global_latest(
    db_session: Session,
) -> None:
    lab_id = uuid4()
    now = datetime.now(timezone.utc)
    older = uuid4()
    newer = uuid4()
    _seed_session(
        db_session,
        session_id=older,
        lab_id=lab_id,
        owner_username="learner-a",
        created_at=now - timedelta(minutes=2),
    )
    _seed_session(
        db_session,
        session_id=newer,
        lab_id=lab_id,
        owner_username="learner-b",
        created_at=now,
    )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/labs/{lab_id}/latest-session",
            headers=_auth_header(token="local:admin-user:admin"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["session_id"] == str(newer)


def test_get_latest_lab_session_not_found_when_no_owned_sessions(
    db_session: Session,
) -> None:
    owner_username = "learner-none"
    other_username = "learner-other"
    lab_id = uuid4()
    _seed_session(
        db_session,
        session_id=uuid4(),
        lab_id=lab_id,
        owner_username=other_username,
        created_at=datetime.now(timezone.utc),
    )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/labs/{lab_id}/latest-session",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404


def test_get_latest_lab_session_requires_auth(db_session: Session) -> None:
    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/labs/{uuid4()}/latest-session",
            headers={"Authorization": "Bearer invalid-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
