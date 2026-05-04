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
    SessionFeedbackModel,
    SessionHintModel,
    SessionModel,
    SessionObjectiveModel,
)
from apps.control_plane.src.interfaces.http.main import app
from apps.control_plane.src.interfaces.http.dependencies import (
    get_worker_heartbeat_repository,
)
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.interfaces.runtime.session_hint_unlock_worker import (
    run_once as run_hint_unlock_worker_once,
)
from apps.control_plane.src.interfaces.runtime.session_completed_worker import (
    run_once as run_session_completed_worker_once,
)
from apps.control_plane.src.interfaces.runtime.session_objective_completed_worker import (
    run_once as run_objective_worker_once,
)
from apps.control_plane.src.application.session_completion.service import (
    process_pending_session_completed_once,
)
from apps.control_plane.src.application.session_objectives.service import (
    process_pending_objective_completed_once,
)
from apps.control_plane.src.infrastructure.persistence.outbox import SQLAlchemyOutbox
from apps.control_plane.src.infrastructure.persistence.outbox_session_objective_completed import (
    SQLAlchemyOutboxSessionObjectiveCompleted,
)
from apps.control_plane.src.infrastructure.persistence.outbox_session_completed import (
    SQLAlchemyOutboxSessionCompleted,
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


def _make_session(
    session_id: UUID, owner_username: str, **overrides: object
) -> SessionModel:
    defaults: dict[str, object] = {
        "id": session_id,
        "lab_id": uuid4(),
        "lab_version_id": uuid4(),
        "owner_user_id": _owner_user_id(owner_username),
        "state": SessionState.ACTIVE.value,
        "runtime_substate": "WAITING_FOR_INPUT",
        "resume_mode": "hot_resume",
        "last_transition_actor": "seed",
        "last_transition_reason": None,
    }
    defaults.update(overrides)
    return SessionModel(**defaults)


_LAB3_OBJECTIVES = (
    ("malicious_vendor_memory_written", "Malicious instruction written to memory", 0),
    ("poisoned_memory_retrieved_for_invoice", "Malicious instruction retrieved", 1),
    ("payment_routed_to_attacker_account", "Payment Routed To Attacker Account", 2),
)


def _add_lab3_objectives(
    db: Session,
    session_id: UUID,
    lab_id: UUID,
    lab_version_id: UUID,
    now: datetime,
    reason_code: str,
    trigger_event_offset: int,
    include_lab_objectives: bool = False,
) -> None:
    for objective_key, label, sort_order in _LAB3_OBJECTIVES:
        if include_lab_objectives:
            db.add(
                LabObjectivesModel(
                    lab_version_id=lab_version_id,
                    objective_key=objective_key,
                    label=label,
                    sort_order=sort_order,
                )
            )
        db.add(
            SessionObjectiveModel(
                session_id=session_id,
                objective_key=objective_key,
                label=label,
                status="pending",
                sort_order=sort_order,
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
                    "lab_id": str(lab_id),
                    "lab_version_id": str(lab_version_id),
                    "objective_key": objective_key,
                    "reason_code": reason_code,
                    "trigger_event_index": trigger_event_offset + sort_order,
                    "occurred_at": now.isoformat(),
                    "idempotency_key": (
                        f"objective:{session_id}:{objective_key}:{trigger_event_offset + sort_order}"
                    ),
                    "source": "evaluator",
                    "evaluator_version": 1,
                },
            )
        )


def test_get_session_metadata_returns_200(db_session: Session) -> None:
    session_id = uuid4()
    lab_id = uuid4()
    lab_version_id = uuid4()
    owner_username = "owner-user"

    db_session.add(
        _make_session(
            session_id, owner_username, lab_id=lab_id, lab_version_id=lab_version_id
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
    assert session["feedback_items"] == []
    assert session["feedback"] == []
    assert session["unread_feedback_count"] == 0


def test_get_session_metadata_rehydrates_persisted_feedback_and_unread_count(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "owner-user"
    now = datetime.now(timezone.utc)

    db_session.add(_make_session(session_id, owner_username))
    db_session.flush()
    db_session.add_all(
        [
            SessionFeedbackModel(
                id=uuid4(),
                session_id=session_id,
                feedback_key="lab1_benign_email_no_progress",
                reason_code="BENIGN_EMAIL_NOT_PROGRESSING",
                message="This action did not advance the objective.",
                severity="info",
                trigger_event_index=3,
                created_at=now,
                seen_at=None,
                idempotency_key="feedback:session:3:benign",
            ),
            SessionFeedbackModel(
                id=uuid4(),
                session_id=session_id,
                feedback_key="lab1_tool_call_off_path",
                reason_code="TOOL_CALL_OFF_PATH",
                message="This action is valid but did not advance progress.",
                severity="warning",
                trigger_event_index=4,
                created_at=now + timedelta(seconds=1),
                seen_at=now + timedelta(seconds=2),
                idempotency_key="feedback:session:4:offpath",
            ),
        ]
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

    first_feedback = first.json()["session"]["feedback"]
    second_feedback = second.json()["session"]["feedback"]
    first_feedback_items = first.json()["session"]["feedback_items"]
    second_feedback_items = second.json()["session"]["feedback_items"]

    assert len(first_feedback) == 2
    assert len(second_feedback) == 2
    assert len(first_feedback_items) == 2
    assert len(second_feedback_items) == 2
    assert first_feedback_items == first_feedback
    assert second_feedback_items == second_feedback
    assert first_feedback[0]["feedback_key"] == "lab1_benign_email_no_progress"
    assert first_feedback[0]["reason_code"] == "BENIGN_EMAIL_NOT_PROGRESSING"
    assert first_feedback[0]["message"] == "This action did not advance the objective."
    assert first_feedback[0]["severity"] == "info"
    assert first_feedback[0]["trigger_event_index"] == 3
    assert first_feedback[0]["seen_at"] is None
    assert first_feedback[1]["feedback_key"] == "lab1_tool_call_off_path"
    assert first_feedback[1]["reason_code"] == "TOOL_CALL_OFF_PATH"
    assert (
        first_feedback[1]["message"]
        == "This action is valid but did not advance progress."
    )
    assert first_feedback[1]["severity"] == "warning"
    assert first_feedback[1]["trigger_event_index"] == 4
    assert first_feedback[1]["seen_at"] is not None
    assert first.json()["session"]["unread_feedback_count"] == 1
    assert second.json()["session"]["unread_feedback_count"] == 1


def test_get_session_metadata_zero_feedback_returns_empty_items_and_zero_unread(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "zero-feedback-owner"

    db_session.add(_make_session(session_id, owner_username))
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
    assert session["feedback_items"] == []
    assert session["feedback"] == []
    assert session["unread_feedback_count"] == 0


@pytest.mark.usefixtures("engine")
def test_get_session_metadata_feedback_stable_across_refresh_and_reconnect() -> None:
    session_id = uuid4()
    owner_username = "feedback-reconnect-owner"
    now = datetime.now(timezone.utc)

    with SessionFactory() as db:
        db.add(_make_session(session_id, owner_username))
        db.flush()
        db.add_all(
            [
                SessionFeedbackModel(
                    id=uuid4(),
                    session_id=session_id,
                    feedback_key="lab1_benign_email_no_progress",
                    reason_code="BENIGN_EMAIL_NOT_PROGRESSING",
                    message="This action did not advance the objective.",
                    severity="info",
                    trigger_event_index=11,
                    created_at=now,
                    seen_at=None,
                    idempotency_key="feedback:reconnect:11:benign",
                ),
                SessionFeedbackModel(
                    id=uuid4(),
                    session_id=session_id,
                    feedback_key="lab1_tool_call_off_path",
                    reason_code="TOOL_CALL_OFF_PATH",
                    message="This action is valid but did not advance progress.",
                    severity="warning",
                    trigger_event_index=12,
                    created_at=now + timedelta(seconds=1),
                    seen_at=now + timedelta(seconds=3),
                    idempotency_key="feedback:reconnect:12:offpath",
                ),
            ]
        )
        db.commit()

    app.dependency_overrides[get_db_session] = _override_db_session_factory()
    try:
        first_client = TestClient(app)
        first_response = first_client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
        first_client.close()

        second_client = TestClient(app)
        second_response = second_client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
        second_client.close()
    finally:
        app.dependency_overrides.clear()

    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_session = first_response.json()["session"]
    second_session = second_response.json()["session"]

    assert first_session["feedback_items"] == second_session["feedback_items"]
    assert first_session["feedback"] == second_session["feedback"]
    assert first_session["unread_feedback_count"] == 1
    assert second_session["unread_feedback_count"] == 1


def test_get_session_metadata_returns_404_for_missing(db_session: Session) -> None:
    missing_id = uuid4()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
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

    db_session.add(_make_session(session_id, owner_username))
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

    db_session.add(_make_session(session_id, owner_username))
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

    db_session.add(_make_session(session_id, owner_username, lab_difficulty="easy"))
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
        _make_session(
            session_id,
            owner_username,
            lab_id=lab_id,
            lab_version_id=lab_version_id,
            state=SessionState.COMPLETED.value,
            runtime_substate=None,
            started_at=started_at,
            ended_at=ended_at,
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
        _make_session(
            session_id,
            owner_username,
            state=SessionState.COMPLETED.value,
            runtime_substate=None,
            started_at=datetime.now(timezone.utc),
            ended_at=completed_at,
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


def test_get_session_metadata_completed_failure_fields_persist_across_refresh(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "completion-failure-owner"
    completed_at = datetime.now(timezone.utc)

    db_session.add(
        _make_session(
            session_id,
            owner_username,
            started_at=datetime.now(timezone.utc),
            ended_at=None,
            completion_status="completed_failure",
            completed_at=completed_at,
            completion_reason_code="USER_ABORTED",
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

    assert first_session["completion_status"] == "completed_failure"
    assert first_session["completion_reason_code"] == "USER_ABORTED"
    assert first_session["completed_at"] is not None
    assert second_session["completion_status"] == "completed_failure"
    assert second_session["completion_reason_code"] == "USER_ABORTED"
    assert second_session["completed_at"] == first_session["completed_at"]


@pytest.mark.usefixtures("engine")
def test_get_session_metadata_marks_provisioning_stalled_when_heartbeat_missing(
    db_session: Session,
) -> None:
    session_id = uuid4()
    owner_username = "stall-owner"
    stale_created_at = datetime.now(timezone.utc) - timedelta(minutes=7)

    db_session.add(
        _make_session(
            session_id,
            owner_username,
            state=SessionState.PROVISIONING.value,
            runtime_substate="PENDING",
            created_at=stale_created_at,
        )
    )
    db_session.flush()

    class _NoHeartbeatRepo:
        def read_heartbeat(self, worker_name: str) -> None:
            assert worker_name == "provisioning_worker"
            return None

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    app.dependency_overrides[get_worker_heartbeat_repository] = _NoHeartbeatRepo
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
        session = _make_session(
            uuid4(),
            owner_username,
            lab_id=lab_3_id,
            lab_version_id=lab_3_version_id,
            lab_difficulty="medium",
        )
        db.add(session)
        db.flush()
        session_id = session.id

        _add_lab3_objectives(
            db,
            session_id,
            lab_3_id,
            lab_3_version_id,
            now,
            reason_code="LAB3_SMOKE",
            trigger_event_offset=700,
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

    session = _make_session(
        uuid4(),
        owner_username,
        lab_id=lab_id,
        lab_version_id=lab_version_id,
        lab_difficulty="medium",
    )
    db_session.add(session)
    db_session.flush()
    session_id = session.id
    now = datetime.now(timezone.utc)

    _add_lab3_objectives(
        db_session,
        session_id,
        lab_id,
        lab_version_id,
        now,
        reason_code="LAB3_COMPLETION_REFRESH",
        trigger_event_offset=900,
        include_lab_objectives=True,
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


@pytest.mark.usefixtures("engine")
def test_completion_projects_through_workers_and_persists_in_metadata() -> None:
    owner_username = "completion-worker-owner"
    now = datetime.now(timezone.utc)
    session_id = uuid4()
    lab_id = uuid4()
    lab_version_id = uuid4()

    with SessionFactory() as db:
        db.add(
            _make_session(
                session_id,
                owner_username,
                lab_id=lab_id,
                lab_version_id=lab_version_id,
                lab_difficulty="medium",
            )
        )
        db.add(
            OutboxEventModel(
                event_type="session.completed.v1",
                aggregate_id=session_id,
                status="pending",
                payload={
                    "session_id": str(session_id),
                    "lab_id": str(lab_id),
                    "lab_version_id": str(lab_version_id),
                    "outcome": "completed_success",
                    "completion_reason_code": "ALL_REQUIRED_OBJECTIVES_COMPLETED",
                    "trigger_event_index": 1200,
                    "occurred_at": now.isoformat(),
                    "idempotency_key": (
                        "session_completed:"
                        f"{session_id}:completed_success:"
                        "all_required_objectives_completed:1200"
                    ),
                },
            )
        )
        db.commit()

    run_session_completed_worker_once()

    app.dependency_overrides[get_db_session] = _override_db_session_factory()
    try:
        client = TestClient(app)
        first = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
        run_session_completed_worker_once()
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


def test_objective_flow_emits_one_terminal_completion_and_metadata_is_stable_on_replay(
    db_session: Session,
) -> None:
    owner_username = "completion-e2e-owner"
    lab_id = UUID("33333333-3333-3333-3333-333333333333")
    lab_version_id = UUID("33333333-3333-3333-3333-aaaaaaaaaaa3")
    session = _make_session(
        uuid4(),
        owner_username,
        lab_id=lab_id,
        lab_version_id=lab_version_id,
        lab_difficulty="medium",
    )
    db_session.add(session)
    db_session.flush()
    session_id = session.id
    now = datetime.now(timezone.utc)

    _add_lab3_objectives(
        db_session,
        session_id,
        lab_id,
        lab_version_id,
        now,
        reason_code="LAB3_E2E_COMPLETION",
        trigger_event_offset=1300,
        include_lab_objectives=True,
    )
    db_session.flush()

    objective_result = process_pending_objective_completed_once(
        outbox_repo=SQLAlchemyOutboxSessionObjectiveCompleted(db=db_session),
        event_outbox_repo=SQLAlchemyOutbox(db=db_session),
        template_reader=SQLAlchemyLabObjectiveTemplateRepository(db=db_session),
        objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
        completion_writer=SQLAlchemySessionRepository(db=db_session),
    )
    completion_projection = process_pending_session_completed_once(
        outbox_repo=SQLAlchemyOutboxSessionCompleted(db=db_session),
        completion_writer=SQLAlchemySessionRepository(db=db_session),
    )
    db_session.flush()
    assert objective_result.succeeded_count == 3
    assert completion_projection.succeeded_count == 1
    assert completion_projection.failed_count == 0
    assert completion_projection.retried_count == 0

    completed_events = (
        db_session.query(OutboxEventModel)
        .filter(
            OutboxEventModel.event_type == "session.completed.v1",
            OutboxEventModel.aggregate_id == session_id,
        )
        .all()
    )
    assert len(completed_events) == 1
    assert completed_events[0].status == "processed"

    # Replay a duplicate terminal objective-completed event.
    db_session.add(
        OutboxEventModel(
            event_type="session.objective.completed.v1",
            aggregate_id=session_id,
            status="pending",
            payload={
                "session_id": str(session_id),
                "lab_id": str(lab_id),
                "lab_version_id": str(lab_version_id),
                "objective_key": "payment_routed_to_attacker_account",
                "reason_code": "LAB3_E2E_COMPLETION_REPLAY",
                "trigger_event_index": 1310,
                "occurred_at": (now + timedelta(minutes=1)).isoformat(),
                "idempotency_key": (
                    f"objective:{session_id}:payment_routed_to_attacker_account:1310"
                ),
                "source": "evaluator",
                "evaluator_version": 1,
            },
        )
    )
    db_session.flush()

    app.dependency_overrides[get_db_session] = _override_db_session(db_session)
    try:
        client = TestClient(app)
        first_response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )

        replay_objective_result = process_pending_objective_completed_once(
            outbox_repo=SQLAlchemyOutboxSessionObjectiveCompleted(db=db_session),
            event_outbox_repo=SQLAlchemyOutbox(db=db_session),
            template_reader=SQLAlchemyLabObjectiveTemplateRepository(db=db_session),
            objective_writer=SQLAlchemySessionObjectiveWriterRepository(db=db_session),
            completion_writer=SQLAlchemySessionRepository(db=db_session),
        )
        replay_completion_projection = process_pending_session_completed_once(
            outbox_repo=SQLAlchemyOutboxSessionCompleted(db=db_session),
            completion_writer=SQLAlchemySessionRepository(db=db_session),
        )
        db_session.flush()

        second_response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers=_auth_header(token=f"local:{owner_username}"),
        )
    finally:
        app.dependency_overrides.clear()

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    first_session = first_response.json()["session"]
    second_session = second_response.json()["session"]
    assert replay_objective_result.succeeded_count == 1
    assert replay_completion_projection.succeeded_count == 0

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

    replay_completed_events = (
        db_session.query(OutboxEventModel)
        .filter(
            OutboxEventModel.event_type == "session.completed.v1",
            OutboxEventModel.aggregate_id == session_id,
        )
        .all()
    )
    assert len(replay_completed_events) == 1
