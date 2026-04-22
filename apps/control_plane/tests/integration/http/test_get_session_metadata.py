from datetime import datetime, timedelta, timezone
from uuid import UUID, NAMESPACE_URL, uuid4, uuid5

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState
from apps.control_plane.src.infrastructure.persistence.db import SessionFactory
from apps.control_plane.src.infrastructure.persistence.models import (
    LabObjectivesModel,
    OutboxEventModel,
    SessionHintModel,
    SessionModel,
    SessionObjectiveModel,
)
import apps.control_plane.src.interfaces.http.main as main_module
from apps.control_plane.src.interfaces.http.main import app
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.interfaces.runtime.session_hint_unlock_worker import (
    run_once as run_hint_unlock_worker_once,
)
from apps.control_plane.src.interfaces.runtime.session_objective_completed_worker import (
    run_once as run_objective_worker_once,
)
from apps.control_plane.src.application.session_objectives.service import (
    process_pending_objective_completed_once,
)
from apps.control_plane.src.infrastructure.persistence.outbox import SQLAlchemyOutbox
from apps.control_plane.src.infrastructure.persistence.outbox_session_objective_completed import (
    SQLAlchemyOutboxSessionObjectiveCompleted,
)
from apps.control_plane.src.infrastructure.persistence.session_objectives_repository import (
    SQLAlchemyLabObjectiveTemplateRepository,
    SQLAlchemySessionObjectiveWriterRepository,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionRepository,
)


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


def _override_db_session_factory():
    def _dependency_override():
        db = SessionFactory()
        try:
            yield db
        finally:
            db.close()

    return _dependency_override


def test_get_session_metadata_returns_200(db_session: Session) -> None:
    session_id = uuid4()
    lab_id = uuid4()
    lab_version_id = uuid4()
    owner_username = "owner-user"

    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=lab_id,
            lab_version_id=lab_version_id,
            owner_user_id=_owner_user_id(owner_username),
            state=SessionState.ACTIVE.value,
            runtime_substate="WAITING_FOR_INPUT",
            resume_mode="hot_resume",
            last_transition_actor="seed",
            last_transition_reason=None,
        )
    )
    db_session.flush()
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            SessionHintModel(
                id=uuid4(),
                session_id=session_id,
                hint_key="hint_1",
                text="Ask the assistant what tools are available to it.",
                sort_order=0,
                status="unlocked",
                unlock_at=now,
                unlocked_at=now,
                seen_at=None,
            ),
            SessionHintModel(
                id=uuid4(),
                session_id=session_id,
                hint_key="hint_2",
                text="The assistant can read emails but can it tell malicious instructions?",
                sort_order=1,
                status="pending",
                unlock_at=now + timedelta(minutes=5),
                unlocked_at=None,
                seen_at=None,
            ),
        ]
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert "session" in body
    session = body["session"]

    assert session["id"] == str(session_id)
    assert session["lab_id"] == str(lab_id)
    assert session["lab_version_id"] == str(lab_version_id)
    assert session["lab_difficulty"] == "medium"
    assert session["state"] == SessionState.ACTIVE.value
    assert session["runtime_substate"] == "WAITING_FOR_INPUT"
    assert session["resume_mode"] == "hot_resume"
    assert session["interactive"] is True
    assert session["created_at"] is not None
    assert session["started_at"] is None
    assert session["ended_at"] is None
    assert session["completion_status"] == "in_progress"
    assert session["completed_at"] is None
    assert session["completion_reason_code"] is None
    assert len(session["hints"]) == 2
    assert session["hints"][0]["hint_key"] == "hint_1"
    assert session["hints"][0]["status"] == "unlocked"
    assert session["hints"][1]["hint_key"] == "hint_2"
    assert session["hints"][1]["status"] == "pending"
    assert session["unread_hint_count"] == 1


def test_get_session_metadata_returns_404_for_missing(db_session: Session) -> None:
    missing_id = uuid4()

    app.dependency_overrides[get_db_session] = _override_db_session_factory()
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions/{missing_id}",
            headers=_auth_header(token="local:any-user"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "SESSION_NOT_FOUND"
    assert body["error"]["message"] == "Session not found"
    assert body["error"]["retryable"] is False
    assert body["error"]["details"]["session_id"] == str(missing_id)


def test_get_session_metadata_returns_403_for_non_owner(db_session: Session) -> None:
    session_id = uuid4()
    owner_username = "owner-user"
    requester_username = "different-user"

    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=uuid4(),
            lab_version_id=uuid4(),
            owner_user_id=_owner_user_id(owner_username),
            state=SessionState.ACTIVE.value,
            runtime_substate="WAITING_FOR_INPUT",
            resume_mode="hot_resume",
            last_transition_actor="seed",
            last_transition_reason=None,
        )
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{requester_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "FORBIDDEN"
    assert body["error"]["retryable"] is False


def test_get_session_metadata_returns_200_for_admin_non_owner(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "owner-user"

    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=uuid4(),
            lab_version_id=uuid4(),
            owner_user_id=_owner_user_id(owner_username),
            state=SessionState.ACTIVE.value,
            runtime_substate="WAITING_FOR_INPUT",
            resume_mode="hot_resume",
            last_transition_actor="seed",
            last_transition_reason=None,
        )
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token="local:admin-user:admin"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200


def test_get_session_metadata_returns_lab_difficulty_when_set(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "difficulty-owner"

    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=uuid4(),
            lab_version_id=uuid4(),
            lab_difficulty="easy",
            owner_user_id=_owner_user_id(owner_username),
            state=SessionState.ACTIVE.value,
            runtime_substate="WAITING_FOR_INPUT",
            resume_mode="hot_resume",
            last_transition_actor="seed",
            last_transition_reason=None,
        )
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    session = response.json()["session"]
    assert session["lab_difficulty"] == "easy"


def test_get_session_metadata_returns_terminal_session_with_interactive_false(
    db_session: Session,
) -> None:
    session_id = uuid4()
    lab_id = uuid4()
    lab_version_id = uuid4()
    owner_username = "terminal-owner"
    started_at = datetime.now(timezone.utc)
    ended_at = datetime.now(timezone.utc)

    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=lab_id,
            lab_version_id=lab_version_id,
            owner_user_id=_owner_user_id(owner_username),
            state=SessionState.COMPLETED.value,
            runtime_substate=None,
            resume_mode="hot_resume",
            started_at=started_at,
            ended_at=ended_at,
            last_transition_actor="seed",
            last_transition_reason="LAB_COMPLETED",
        )
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert "session" in body
    session = body["session"]

    assert session["id"] == str(session_id)
    assert session["lab_id"] == str(lab_id)
    assert session["lab_version_id"] == str(lab_version_id)
    assert session["state"] == SessionState.COMPLETED.value
    assert session["runtime_substate"] is None
    assert session["interactive"] is False
    assert session["created_at"] is not None
    assert session["started_at"] is not None
    assert session["ended_at"] is not None


def test_get_session_metadata_completion_fields_persist_across_refresh(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "completion-owner"
    completed_at = datetime.now(timezone.utc)

    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=uuid4(),
            lab_version_id=uuid4(),
            owner_user_id=_owner_user_id(owner_username),
            state=SessionState.COMPLETED.value,
            runtime_substate=None,
            resume_mode="hot_resume",
            started_at=datetime.now(timezone.utc),
            ended_at=completed_at,
            last_transition_actor="seed",
            last_transition_reason="LAB_COMPLETED",
            completion_status="completed_success",
            completed_at=completed_at,
            completion_reason_code="ALL_OBJECTIVES_COMPLETED",
        )
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        first = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
        second = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert second.status_code == 200
    first_session = first.json()["session"]
    second_session = second.json()["session"]

    assert first_session["completion_status"] == "completed_success"
    assert first_session["completion_reason_code"] == "ALL_OBJECTIVES_COMPLETED"
    assert first_session["completed_at"] is not None
    assert second_session["completion_status"] == "completed_success"
    assert second_session["completion_reason_code"] == "ALL_OBJECTIVES_COMPLETED"
    assert second_session["completed_at"] == first_session["completed_at"]


@pytest.mark.usefixtures("engine")
def test_get_session_metadata_marks_provisioning_stalled_when_heartbeat_missing(
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = uuid4()
    owner_username = "stall-owner"
    stale_created_at = datetime.now(timezone.utc) - timedelta(minutes=7)

    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=uuid4(),
            lab_version_id=uuid4(),
            owner_user_id=_owner_user_id(owner_username),
            state=SessionState.PROVISIONING.value,
            runtime_substate="PENDING",
            resume_mode="hot_resume",
            created_at=stale_created_at,
            last_transition_actor="seed",
            last_transition_reason=None,
        )
    )
    db_session.flush()

    def _fake_read_heartbeat(self: object, worker_name: str) -> None:
        assert worker_name == "provisioning_worker"
        return None

    monkeypatch.setattr(
        main_module.SQLAlchemyWorkerHeartbeatRepository,
        "read_heartbeat",
        _fake_read_heartbeat,
    )

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    session = response.json()["session"]
    assert session["state"] == SessionState.PROVISIONING.value
    assert session["provisioning_stalled"] is True
    assert session["provisioning_stall_reason_code"] == "SESSION_PROVISIONING_STALLED"


@pytest.mark.usefixtures("engine")
def test_lab3_smoke_objective_and_hint_state_stable_across_refresh_reconnect() -> None:
    lab_3_id = UUID("33333333-3333-3333-3333-333333333333")
    lab_3_version_id = UUID("33333333-3333-3333-3333-aaaaaaaaaaa3")
    owner_username = "lab3-smoke-owner"
    now = datetime.now(timezone.utc)

    with SessionFactory() as db:
        session = SessionModel(
            id=uuid4(),
            lab_id=lab_3_id,
            lab_version_id=lab_3_version_id,
            owner_user_id=_owner_user_id(owner_username),
            state=SessionState.ACTIVE.value,
            runtime_substate="WAITING_FOR_INPUT",
            resume_mode="hot_resume",
            last_transition_actor="seed",
            last_transition_reason=None,
            lab_difficulty="medium",
        )
        db.add(session)
        db.flush()
        session_id = session.id

        objective_keys = (
            "malicious_vendor_memory_written",
            "poisoned_memory_retrieved_for_invoice",
            "payment_routed_to_attacker_account",
        )
        objective_labels = (
            "Malicious Vendor Memory Written",
            "Poisoned Memory Retrieved For Invoice",
            "Payment Routed To Attacker Account",
        )
        for index, (objective_key, label) in enumerate(
            zip(objective_keys, objective_labels, strict=True)
        ):
            db.add(
                SessionObjectiveModel(
                    session_id=session_id,
                    objective_key=objective_key,
                    label=label,
                    status="pending",
                    sort_order=index,
                    completed_at=None,
                )
            )
            db.add(
                OutboxEventModel(
                    event_type="session.objective.completed.v1",
                    aggregate_id=session_id,
                    status="pending",
                    payload={
                        "session_id": str(session_id),
                        "lab_id": str(lab_3_id),
                        "lab_version_id": str(lab_3_version_id),
                        "objective_key": objective_key,
                        "reason_code": "LAB3_SMOKE",
                        "trigger_event_index": 700 + index,
                        "occurred_at": now.isoformat(),
                        "idempotency_key": (
                            f"objective:{session_id}:{objective_key}:{700 + index}"
                        ),
                        "source": "evaluator",
                        "evaluator_version": 1,
                    },
                )
            )

        db.add_all(
            [
                SessionHintModel(
                    id=uuid4(),
                    session_id=session_id,
                    hint_key="hint_1",
                    text="Lab 3 hint 1",
                    sort_order=0,
                    unlock_at=now - timedelta(seconds=5),
                    status="pending",
                ),
                SessionHintModel(
                    id=uuid4(),
                    session_id=session_id,
                    hint_key="hint_2",
                    text="Lab 3 hint 2",
                    sort_order=1,
                    unlock_at=now + timedelta(minutes=20),
                    status="pending",
                ),
            ]
        )
        db.commit()

    run_objective_worker_once()
    run_hint_unlock_worker_once()

    app.dependency_overrides[get_db_session] = _override_db_session_factory()
    try:
        client = TestClient(app)
        first_response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
        assert first_response.status_code == 200
        first_session = first_response.json()["session"]
        assert [chip["status"] for chip in first_session["progress_chips"]] == [
            "complete",
            "complete",
            "complete",
        ]
        assert [hint["status"] for hint in first_session["hints"]] == [
            "unlocked",
            "pending",
        ]
        assert first_session["unread_hint_count"] == 1

        # Replay/reprocessing + reconnect should keep projection stable.
        run_objective_worker_once()
        run_hint_unlock_worker_once()

        second_response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
        assert second_response.status_code == 200
        second_session = second_response.json()["session"]
    finally:
        app.dependency_overrides.clear()

    assert [chip["status"] for chip in second_session["progress_chips"]] == [
        "complete",
        "complete",
        "complete",
    ]
    assert [hint["status"] for hint in second_session["hints"]] == [
        "unlocked",
        "pending",
    ]
    assert second_session["unread_hint_count"] == 1


def test_completion_fields_persist_across_refresh_after_objective_projection(
    db_session: Session,
) -> None:
    lab_id = UUID("33333333-3333-3333-3333-333333333333")
    lab_version_id = UUID("33333333-3333-3333-3333-aaaaaaaaaaa3")
    owner_username = "completion-refresh-owner"
    now = datetime.now(timezone.utc)

    session = SessionModel(
        id=uuid4(),
        lab_id=lab_id,
        lab_version_id=lab_version_id,
        owner_user_id=_owner_user_id(owner_username),
        state=SessionState.ACTIVE.value,
        runtime_substate="WAITING_FOR_INPUT",
        resume_mode="hot_resume",
        last_transition_actor="seed",
        last_transition_reason=None,
        lab_difficulty="medium",
    )
    db_session.add(session)
    db_session.flush()
    session_id = session.id

    objectives = (
        (
            "malicious_vendor_memory_written",
            "Malicious Vendor Memory Written",
            0,
        ),
        (
            "poisoned_memory_retrieved_for_invoice",
            "Poisoned Memory Retrieved For Invoice",
            1,
        ),
        (
            "payment_routed_to_attacker_account",
            "Payment Routed To Attacker Account",
            2,
        ),
    )
    for objective_key, label, sort_order in objectives:
        db_session.add(
            LabObjectivesModel(
                lab_version_id=lab_version_id,
                objective_key=objective_key,
                label=label,
                sort_order=sort_order,
            )
        )
        db_session.add(
            SessionObjectiveModel(
                session_id=session_id,
                objective_key=objective_key,
                label=label,
                status="pending",
                sort_order=sort_order,
                completed_at=None,
            )
        )
        db_session.add(
            OutboxEventModel(
                event_type="session.objective.completed.v1",
                aggregate_id=session_id,
                status="pending",
                payload={
                    "session_id": str(session_id),
                    "lab_id": str(lab_id),
                    "lab_version_id": str(lab_version_id),
                    "objective_key": objective_key,
                    "reason_code": "LAB3_COMPLETION_REFRESH",
                    "trigger_event_index": 900 + sort_order,
                    "occurred_at": now.isoformat(),
                    "idempotency_key": (
                        f"objective:{session_id}:{objective_key}:{900 + sort_order}"
                    ),
                    "source": "evaluator",
                    "evaluator_version": 1,
                },
            )
        )
    db_session.flush()

    projection_result = process_pending_objective_completed_once(
        outbox_repo=SQLAlchemyOutboxSessionObjectiveCompleted(db=db_session),
        event_outbox_repo=SQLAlchemyOutbox(db=db_session),
        template_reader=SQLAlchemyLabObjectiveTemplateRepository(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
        completion_writer=SQLAlchemySessionRepository(db=db_session),
    )
    db_session.flush()
    assert projection_result.succeeded_count == 3

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        first = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
        second = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert second.status_code == 200
    first_session = first.json()["session"]
    second_session = second.json()["session"]
    assert first_session["completion_status"] == "completed_success"
    assert (
        first_session["completion_reason_code"] == "ALL_REQUIRED_OBJECTIVES_COMPLETED"
    )
    assert first_session["completed_at"] is not None
    assert second_session["completion_status"] == "completed_success"
    assert (
        second_session["completion_reason_code"] == "ALL_REQUIRED_OBJECTIVES_COMPLETED"
    )
    assert second_session["completed_at"] == first_session["completed_at"]
