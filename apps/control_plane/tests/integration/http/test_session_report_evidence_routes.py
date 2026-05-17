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
                details={"raw": "second"},
                occurred_at=now,
                trace_version=1,
                event_index=11,
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
                details={"raw": "first"},
                occurred_at=now,
                trace_version=2,
                event_index=7,
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
    assert items[0]["citation_label"] == "E1"
    assert items[0]["evidence_strength"] == "medium"
    mapping = items[0]["objective_mapping"]
    assert isinstance(mapping, list)
    assert len(mapping) == 1
    assert mapping[0]["objective_key"].endswith("attack_delivery")
    assert mapping[0]["label"] == "Attack email delivery confirmed"
    assert mapping[0]["rubric_target"] == "attack_delivery_step"


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
                        "details": {"client": "ignored"},
                        "occurred_at": datetime.now(timezone.utc).isoformat(),
                        "trace_version": 99,
                        "event_index": 99,
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
                        "details": {"client": "ignored"},
                        "occurred_at": datetime.now(timezone.utc).isoformat(),
                        "trace_version": 99,
                        "event_index": 42,
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
    assert [item["trace_version"] for item in items] == [1, 1]
    assert [item["event_index"] for item in items] == [1, 2]


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
                        "details": None,
                        "occurred_at": datetime.now(timezone.utc).isoformat(),
                        "trace_version": 1,
                        "event_index": 0,
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
                        "details": None,
                        "occurred_at": datetime.now(timezone.utc).isoformat(),
                        "trace_version": 1,
                        "event_index": 1,
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
                        "details": None,
                        "occurred_at": datetime.now(timezone.utc).isoformat(),
                        "trace_version": 1,
                        "event_index": 0,
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


def test_post_import_selected_evidence_uses_persisted_selection_by_default(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "owner-import-default"
    _seed_session(db_session, session_id=session_id, owner_username=owner_username)
    now = datetime.now(timezone.utc)
    event_a = uuid4()
    event_b = uuid4()
    db_session.add_all(
        [
            SessionReportEvidenceModel(
                id=uuid4(),
                session_id=session_id,
                event_id=event_a,
                position=0,
                title="A",
                description=None,
                details={"x": 1},
                occurred_at=now,
                trace_version=1,
                event_index=10,
                evidence_type="exploit_step",
                objective_keys=["lab1.attack_delivery"],
                why_it_matters=None,
                default_priority="medium",
                student_note=None,
            ),
            SessionReportEvidenceModel(
                id=uuid4(),
                session_id=session_id,
                event_id=event_b,
                position=1,
                title="B",
                description=None,
                details={"x": 2},
                occurred_at=now,
                trace_version=1,
                event_index=11,
                evidence_type="exploit_outcome",
                objective_keys=["lab1.token_disclosed"],
                why_it_matters=None,
                default_priority="high",
                student_note=None,
            ),
        ]
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/sessions/{session_id}/report/import-selected-evidence",
            headers=_auth_header(token=f"local:{owner_username}"),
            json={},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["event_id"] for item in items] == [str(event_a), str(event_b)]
    assert [item["citation_label"] for item in items] == ["E1", "E2"]


def test_post_import_selected_evidence_supports_subset_order_override(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "owner-import-override"
    _seed_session(db_session, session_id=session_id, owner_username=owner_username)
    now = datetime.now(timezone.utc)
    event_a = uuid4()
    event_b = uuid4()
    db_session.add_all(
        [
            SessionReportEvidenceModel(
                id=uuid4(),
                session_id=session_id,
                event_id=event_a,
                position=0,
                title="A",
                description=None,
                details=None,
                occurred_at=now,
                trace_version=1,
                event_index=1,
                evidence_type="exploit_step",
                objective_keys=[],
                why_it_matters=None,
                default_priority="low",
                student_note=None,
            ),
            SessionReportEvidenceModel(
                id=uuid4(),
                session_id=session_id,
                event_id=event_b,
                position=1,
                title="B",
                description=None,
                details=None,
                occurred_at=now,
                trace_version=1,
                event_index=2,
                evidence_type="exploit_step",
                objective_keys=[],
                why_it_matters=None,
                default_priority="low",
                student_note=None,
            ),
        ]
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/sessions/{session_id}/report/import-selected-evidence",
            headers=_auth_header(token=f"local:{owner_username}"),
            json={"event_ids": [str(event_b)]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["event_id"] == str(event_b)
    assert items[0]["citation_label"] == "E2"


def test_get_report_evidence_citation_labels_are_deterministic_by_position(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "owner-citation-determinism"
    _seed_session(db_session, session_id=session_id, owner_username=owner_username)
    now = datetime.now(timezone.utc)
    event_a = uuid4()
    event_b = uuid4()
    db_session.add_all(
        [
            SessionReportEvidenceModel(
                id=uuid4(),
                session_id=session_id,
                event_id=event_a,
                position=9,
                title="Ninth position",
                description=None,
                details=None,
                occurred_at=now,
                trace_version=1,
                event_index=1,
                evidence_type="exploit_step",
                objective_keys=[],
                why_it_matters=None,
                default_priority="low",
                student_note=None,
            ),
            SessionReportEvidenceModel(
                id=uuid4(),
                session_id=session_id,
                event_id=event_b,
                position=3,
                title="Third position",
                description=None,
                details=None,
                occurred_at=now,
                trace_version=1,
                event_index=2,
                evidence_type="exploit_step",
                objective_keys=[],
                why_it_matters=None,
                default_priority="low",
                student_note=None,
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
    assert [item["position"] for item in items] == [3, 9]
    assert [item["citation_label"] for item in items] == ["E4", "E10"]


def test_post_import_selected_evidence_rejects_override_not_in_selection(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "owner-import-invalid"
    _seed_session(db_session, session_id=session_id, owner_username=owner_username)
    now = datetime.now(timezone.utc)
    selected_event_id = uuid4()
    db_session.add(
        SessionReportEvidenceModel(
            id=uuid4(),
            session_id=session_id,
            event_id=selected_event_id,
            position=0,
            title="A",
            description=None,
            details=None,
            occurred_at=now,
            trace_version=1,
            event_index=1,
            evidence_type="exploit_step",
            objective_keys=[],
            why_it_matters=None,
            default_priority="low",
            student_note=None,
        )
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/v1/sessions/{session_id}/report/import-selected-evidence",
            headers=_auth_header(token=f"local:{owner_username}"),
            json={"event_ids": [str(uuid4())]},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_REPORT_EVIDENCE"
