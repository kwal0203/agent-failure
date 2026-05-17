from datetime import datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.models import (
    SessionModel,
    SessionReportEvidenceModel,
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
) -> SessionModel:
    session = SessionModel(
        id=session_id,
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        owner_user_id=_owner_user_id(owner_username),
        state="ACTIVE",
        last_transition_actor="seed",
        last_transition_reason=None,
    )
    db_session.add(session)
    db_session.flush()
    return session


def _seed_trace_event(
    db_session: Session,
    *,
    session_id: UUID,
    event_id: UUID,
    event_index: int,
    event_type: str,
) -> None:
    db_session.add(
        TraceEventModel(
            event_id=event_id,
            session_id=session_id,
            family="model",
            event_type=event_type,
            occurred_at=datetime.now(timezone.utc),
            source="seed",
            event_index=event_index,
            payload={},
            trace_version=1,
        )
    )
    db_session.flush()


def test_get_report_evidence_forbidden_for_non_owner(db_session: Session) -> None:
    session_id = uuid4()
    _seed_session(db_session, session_id=session_id, owner_username="owner-user")

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions/{session_id}/report-evidence",
            headers=_auth_header(token="local:other-user"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403


def test_get_report_evidence_returns_rows_ordered_by_position(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "owner-get"
    _seed_session(db_session, session_id=session_id, owner_username=owner_username)
    now = datetime.now(timezone.utc)

    first_event_id = uuid4()
    second_event_id = uuid4()
    db_session.add_all(
        [
            SessionReportEvidenceModel(
                id=uuid4(),
                session_id=session_id,
                event_id=first_event_id,
                position=1,
                title="Second",
                description=None,
                occurred_at=now,
                evidence_type="system_context",
                objective_keys=[],
                why_it_matters=None,
                default_priority="low",
                student_note=None,
            ),
            SessionReportEvidenceModel(
                id=uuid4(),
                session_id=session_id,
                event_id=second_event_id,
                position=0,
                title="First",
                description=None,
                occurred_at=now,
                evidence_type="exploit_step",
                objective_keys=["lab1.attack_delivery"],
                why_it_matters="Delivery event",
                default_priority="medium",
                student_note="note",
            ),
        ]
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions/{session_id}/report-evidence",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["position"] for item in items] == [0, 1]
    assert [item["title"] for item in items] == ["First", "Second"]


def test_put_report_evidence_full_replace_and_normalized_positions(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "owner-put"
    _seed_session(db_session, session_id=session_id, owner_username=owner_username)

    event_a = uuid4()
    event_b = uuid4()
    _seed_trace_event(
        db_session,
        session_id=session_id,
        event_id=event_a,
        event_index=1,
        event_type="TOKEN_DISCLOSED",
    )
    _seed_trace_event(
        db_session,
        session_id=session_id,
        event_id=event_b,
        event_index=2,
        event_type="ATTACK_EMAIL_SENT",
    )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.put(
            f"/api/v1/sessions/{session_id}/report-evidence",
            headers=_auth_header(token=f"local:{owner_username}"),
            json={
                "items": [
                    {
                        "event_id": str(event_a),
                        "position": 99,
                        "title": "Token disclosed",
                        "description": "Sensitive token was exposed.",
                        "occurred_at": datetime.now(timezone.utc).isoformat(),
                        "evidence_type": "exploit_outcome",
                        "objective_keys": ["lab1.token_disclosed"],
                        "why_it_matters": "Direct exploit proof",
                        "default_priority": "high",
                        "student_note": None,
                    },
                    {
                        "event_id": str(event_b),
                        "position": 42,
                        "title": "Malicious email received",
                        "description": "Attack delivery",
                        "occurred_at": datetime.now(timezone.utc).isoformat(),
                        "evidence_type": "exploit_step",
                        "objective_keys": ["lab1.attack_delivery"],
                        "why_it_matters": "Shows initial foothold",
                        "default_priority": "medium",
                        "student_note": "include this",
                    },
                ]
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["position"] for item in items] == [0, 1]
    assert [item["event_id"] for item in items] == [str(event_a), str(event_b)]


def test_put_report_evidence_rejects_duplicates(db_session: Session) -> None:
    session_id = uuid4()
    owner_username = "owner-dup"
    _seed_session(db_session, session_id=session_id, owner_username=owner_username)

    event_id = uuid4()
    _seed_trace_event(
        db_session,
        session_id=session_id,
        event_id=event_id,
        event_index=1,
        event_type="TOKEN_DISCLOSED",
    )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.put(
            f"/api/v1/sessions/{session_id}/report-evidence",
            headers=_auth_header(token=f"local:{owner_username}"),
            json={
                "items": [
                    {
                        "event_id": str(event_id),
                        "position": 0,
                        "title": "A",
                        "description": None,
                        "occurred_at": datetime.now(timezone.utc).isoformat(),
                        "evidence_type": "exploit_step",
                        "objective_keys": [],
                        "why_it_matters": None,
                        "default_priority": "low",
                        "student_note": None,
                    },
                    {
                        "event_id": str(event_id),
                        "position": 1,
                        "title": "B",
                        "description": None,
                        "occurred_at": datetime.now(timezone.utc).isoformat(),
                        "evidence_type": "exploit_step",
                        "objective_keys": [],
                        "why_it_matters": None,
                        "default_priority": "low",
                        "student_note": None,
                    },
                ]
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REPORT_EVIDENCE"


def test_put_report_evidence_rejects_non_selectable_trace_event(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "owner-nonselectable"
    _seed_session(db_session, session_id=session_id, owner_username=owner_username)

    event_id = uuid4()
    _seed_trace_event(
        db_session,
        session_id=session_id,
        event_id=event_id,
        event_index=1,
        event_type="SESSION_CREATED",
    )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.put(
            f"/api/v1/sessions/{session_id}/report-evidence",
            headers=_auth_header(token=f"local:{owner_username}"),
            json={
                "items": [
                    {
                        "event_id": str(event_id),
                        "position": 0,
                        "title": "Session created",
                        "description": "noise",
                        "occurred_at": datetime.now(timezone.utc).isoformat(),
                        "evidence_type": "noise",
                        "objective_keys": [],
                        "why_it_matters": None,
                        "default_priority": "low",
                        "student_note": None,
                    }
                ]
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REPORT_EVIDENCE"
