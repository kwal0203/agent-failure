from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from apps.control_plane.src.infrastructure.persistence.models import (
    EvaluatorResultModel,
    SessionModel,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemyEvaluatorRepository,
)


def test_list_results_for_session_returns_ordered_rows(db_session: Session) -> None:
    session_id = uuid4()
    db_session.add(
        SessionModel(
            id=session_id,
            lab_id=uuid4(),
            lab_version_id=uuid4(),
            owner_user_id=uuid4(),
            state="ACTIVE",
            last_transition_actor="seed",
            last_transition_reason=None,
        )
    )
    db_session.flush()

    created_at_1 = datetime.now(timezone.utc)
    created_at_2 = datetime.now(timezone.utc)

    first = EvaluatorResultModel(
        id=uuid4(),
        idempotency_key=f"idempo:{uuid4()}",
        result_type="constraint_violation",
        code="pi.secret_exfiltration_success",
        trigger_event_index=1,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="flag",
        reason_code="PI_SECRET_EXFILTRATION_DETECTED",
        feedback_payload={"matched_value": "FLAG{one}"},
        created_at=created_at_1,
        session_id=session_id,
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        evaluator_version=1,
    )
    second = EvaluatorResultModel(
        id=uuid4(),
        idempotency_key=f"idempo:{uuid4()}",
        result_type="partial_success",
        code="pi.attack_attempt_blocked",
        trigger_event_index=2,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="hint",
        reason_code="PI_ATTACK_ATTEMPT_BLOCKED",
        feedback_payload={"blocked_by": "model_policy"},
        created_at=created_at_2,
        session_id=session_id,
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        evaluator_version=1,
    )
    db_session.add_all([first, second])
    db_session.flush()

    repo = SQLAlchemyEvaluatorRepository(db=db_session)
    rows = repo.list_results_for_session(session_id=session_id)

    assert len(rows) == 2
    assert rows[0].id == first.id
    assert rows[0].result_type == "constraint_violation"
    assert rows[0].code == "pi.secret_exfiltration_success"
    assert rows[1].id == second.id
    assert rows[1].result_type == "partial_success"
    assert rows[1].reason_code == "PI_ATTACK_ATTEMPT_BLOCKED"
