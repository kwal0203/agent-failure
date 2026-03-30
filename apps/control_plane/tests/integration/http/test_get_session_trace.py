from datetime import datetime, timezone
from uuid import UUID, NAMESPACE_URL, uuid4, uuid5

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.models import (
    SessionModel,
    TraceEventModel,
)
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
    db_session: Session, *, session_id: UUID, owner_username: str
) -> None:
    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=uuid4(),
            lab_version_id=uuid4(),
            owner_user_id=_owner_user_id(owner_username),
            state="ACTIVE",
            last_transition_actor="seed",
            last_transition_reason=None,
        )
    )
    db_session.flush()


def test_get_session_trace_excludes_internal_only_events(db_session: Session) -> None:
    session_id = uuid4()
    owner_username = "trace-owner"
    _seed_session(db_session, session_id=session_id, owner_username=owner_username)

    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            TraceEventModel(
                event_id=uuid4(),
                session_id=session_id,
                family="lifecycle",
                event_type="SESSION_CREATED",
                occurred_at=now,
                source="seed",
                event_index=0,
                payload={},
                trace_version=1,
            ),
            TraceEventModel(
                event_id=uuid4(),
                session_id=session_id,
                family="runtime",
                event_type="RUNTIME_PROVISION_ACCEPTED",
                occurred_at=now,
                source="seed",
                event_index=1,
                payload={"runtime_id": "r1"},
                trace_version=1,
            ),
            TraceEventModel(
                event_id=uuid4(),
                session_id=session_id,
                family="learner",
                event_type="USER_PROMPT_SUBMITTED",
                occurred_at=now,
                source="seed",
                event_index=2,
                payload={"content": "hello"},
                trace_version=1,
                actor_user_id=_owner_user_id(owner_username),
            ),
            TraceEventModel(
                event_id=uuid4(),
                session_id=session_id,
                family="model",
                event_type="MODEL_TURN_STARTED",
                occurred_at=now,
                source="seed",
                event_index=3,
                payload={"provider": "openrouter"},
                trace_version=1,
            ),
            TraceEventModel(
                event_id=uuid4(),
                session_id=session_id,
                family="model",
                event_type="MODEL_TURN_COMPLETED",
                occurred_at=now,
                source="seed",
                event_index=4,
                payload={"content": "hi"},
                trace_version=1,
            ),
            TraceEventModel(
                event_id=uuid4(),
                session_id=session_id,
                family="tool",
                event_type="TOOL_CALL_FAILED",
                occurred_at=now,
                source="seed",
                event_index=5,
                payload={"tool_name": "cat", "error_code": "DENIED"},
                trace_version=1,
            ),
        ]
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions/{session_id}/trace",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    events = response.json()["events"]
    assert [(e["family"], e["event_type"]) for e in events] == [
        ("learner", "USER_PROMPT_SUBMITTED"),
        ("model", "MODEL_TURN_COMPLETED"),
    ]


def test_get_session_trace_returns_allowlisted_events_in_event_index_order(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "trace-owner-order"
    _seed_session(db_session, session_id=session_id, owner_username=owner_username)

    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            TraceEventModel(
                event_id=uuid4(),
                session_id=session_id,
                family="model",
                event_type="MODEL_TURN_FAILED",
                occurred_at=now,
                source="seed",
                event_index=9,
                payload={"provider": "openrouter", "error_code": "TIMEOUT"},
                trace_version=1,
            ),
            TraceEventModel(
                event_id=uuid4(),
                session_id=session_id,
                family="learner",
                event_type="USER_PROMPT_SUBMITTED",
                occurred_at=now,
                source="seed",
                event_index=1,
                payload={"content": "hello"},
                trace_version=1,
                actor_user_id=_owner_user_id(owner_username),
            ),
            TraceEventModel(
                event_id=uuid4(),
                session_id=session_id,
                family="model",
                event_type="MODEL_TURN_COMPLETED",
                occurred_at=now,
                source="seed",
                event_index=5,
                payload={"content": "response"},
                trace_version=1,
            ),
        ]
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions/{session_id}/trace",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    events = response.json()["events"]
    assert [e["event_index"] for e in events] == [1, 5, 9]
    assert [(e["family"], e["event_type"]) for e in events] == [
        ("learner", "USER_PROMPT_SUBMITTED"),
        ("model", "MODEL_TURN_COMPLETED"),
        ("model", "MODEL_TURN_FAILED"),
    ]
