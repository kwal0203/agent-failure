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
    state: str = "ACTIVE",
    completion_status: str = "in_progress",
) -> None:
    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=lab_id,
            lab_version_id=uuid4(),
            owner_user_id=_owner_user_id(owner_username),
            state=state,
            completion_status=completion_status,
            last_transition_actor="seed",
            last_transition_reason=None,
            created_at=created_at,
        )
    )
    db_session.flush()


def test_get_sessions_scopes_to_owner_and_orders_newest_first(
    db_session: Session,
) -> None:
    now = datetime.now(timezone.utc)
    lab_id = uuid4()
    owner = "owner-a"
    other = "owner-b"

    own_old = uuid4()
    own_new = uuid4()
    _seed_session(
        db_session,
        session_id=own_old,
        lab_id=lab_id,
        owner_username=owner,
        created_at=now - timedelta(minutes=3),
        completion_status="completed_failure",
    )
    _seed_session(
        db_session,
        session_id=own_new,
        lab_id=lab_id,
        owner_username=owner,
        created_at=now - timedelta(minutes=1),
        completion_status="completed_success",
    )
    _seed_session(
        db_session,
        session_id=uuid4(),
        lab_id=lab_id,
        owner_username=other,
        created_at=now,
    )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions?lab_id={lab_id}&limit=2&sort=created_at:desc",
            headers=_auth_header(token=f"local:{owner}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    sessions = response.json()["sessions"]
    assert [item["session_id"] for item in sessions] == [str(own_new), str(own_old)]
    assert sessions[0]["completion_status"] == "completed_success"
    assert sessions[1]["completion_status"] == "completed_failure"


def test_get_sessions_admin_sees_all_owners(db_session: Session) -> None:
    now = datetime.now(timezone.utc)
    lab_id = uuid4()
    first = uuid4()
    second = uuid4()
    _seed_session(
        db_session,
        session_id=first,
        lab_id=lab_id,
        owner_username="user-1",
        created_at=now - timedelta(minutes=2),
    )
    _seed_session(
        db_session,
        session_id=second,
        lab_id=lab_id,
        owner_username="user-2",
        created_at=now - timedelta(minutes=1),
    )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions?lab_id={lab_id}&limit=5&sort=created_at:desc",
            headers=_auth_header(token="local:admin-user:admin"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    sessions = response.json()["sessions"]
    assert [item["session_id"] for item in sessions] == [str(second), str(first)]


def test_get_sessions_rejects_unsupported_sort(db_session: Session) -> None:
    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions?lab_id={uuid4()}&limit=1&sort=state:asc",
            headers=_auth_header(token="local:owner"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400


def test_get_sessions_requires_auth(db_session: Session) -> None:
    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions?lab_id={uuid4()}&limit=1",
            headers={"Authorization": "Bearer invalid-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
