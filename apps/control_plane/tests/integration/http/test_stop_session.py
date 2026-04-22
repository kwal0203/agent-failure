from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.engine import Engine

from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.models import (
    OutboxEventModel,
    SessionModel,
)
from apps.control_plane.src.interfaces.http.main import app


def _owner_user_id(username: str) -> UUID:
    return uuid5(namespace=NAMESPACE_URL, name=f"local-user:{username}")


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_stop_session_owner_transitions_to_cancelled_and_enqueues_cleanup(
    engine: Engine,
) -> None:
    _ = engine
    session_id = uuid4()
    owner_username = "owner-user"
    runtime_id = "runtime-stop-01"

    with SessionFactory() as db:
        db.add(
            SessionModel(
                id=session_id,
                lab_id=uuid4(),
                lab_version_id=uuid4(),
                owner_user_id=_owner_user_id(owner_username),
                state=SessionState.ACTIVE.value,
                runtime_id=runtime_id,
                runtime_substate="WAITING_FOR_INPUT",
                resume_mode="hot_resume",
                last_transition_actor="seed",
                last_transition_reason=None,
            )
        )
        db.commit()

    client = TestClient(app)
    response = client.post(
        f"/api/v1/sessions/{session_id}/stop",
        headers=_auth_header(token=f"local:{owner_username}"),
    )

    assert response.status_code == 202
    body = response.json()
    assert body["session_id"] == str(session_id)
    assert body["accepted"] is True
    assert body["state"] == SessionState.CANCELLED.value

    with SessionFactory() as db:
        session_row = db.get(SessionModel, session_id)
        assert session_row is not None
        assert session_row.state == SessionState.CANCELLED.value

        cleanup_event = (
            db.execute(
                select(OutboxEventModel).where(
                    OutboxEventModel.aggregate_id == session_id,
                    OutboxEventModel.event_type == "session.cleanup.requested.v1",
                )
            )
            .scalars()
            .one()
        )
        assert cleanup_event.payload["runtime_id"] == runtime_id
        assert cleanup_event.payload["terminal_state"] == SessionState.CANCELLED.value


def test_stop_session_forbidden_for_non_owner(engine: Engine) -> None:
    _ = engine
    session_id = uuid4()
    with SessionFactory() as db:
        db.add(
            SessionModel(
                id=session_id,
                lab_id=uuid4(),
                lab_version_id=uuid4(),
                owner_user_id=_owner_user_id("owner-user"),
                state=SessionState.ACTIVE.value,
                runtime_substate="WAITING_FOR_INPUT",
                resume_mode="hot_resume",
                last_transition_actor="seed",
                last_transition_reason=None,
            )
        )
        db.commit()

    client = TestClient(app)
    response = client.post(
        f"/api/v1/sessions/{session_id}/stop",
        headers=_auth_header(token="local:other-user"),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_stop_session_terminal_state_is_no_op(engine: Engine) -> None:
    _ = engine
    session_id = uuid4()
    owner_username = "owner-user"
    with SessionFactory() as db:
        db.add(
            SessionModel(
                id=session_id,
                lab_id=uuid4(),
                lab_version_id=uuid4(),
                owner_user_id=_owner_user_id(owner_username),
                state=SessionState.CANCELLED.value,
                runtime_substate="TERMINATED",
                resume_mode="hot_resume",
                last_transition_actor="seed",
                last_transition_reason=None,
            )
        )
        db.commit()

    client = TestClient(app)
    response = client.post(
        f"/api/v1/sessions/{session_id}/stop",
        headers=_auth_header(token=f"local:{owner_username}"),
    )

    assert response.status_code == 202
    body = response.json()
    assert body["accepted"] is True
    assert body["state"] == SessionState.CANCELLED.value

    with SessionFactory() as db:
        cleanup_count = (
            db.execute(
                select(OutboxEventModel.id).where(
                    OutboxEventModel.aggregate_id == session_id,
                    OutboxEventModel.event_type == "session.cleanup.requested.v1",
                )
            )
            .scalars()
            .all()
        )
        assert cleanup_count == []
