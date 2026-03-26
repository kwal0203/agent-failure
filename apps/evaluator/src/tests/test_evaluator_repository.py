from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from apps.evaluator.src.application.types import (
    EvaluatorTaskInput,
    EvaluatorTraceEvent,
)
from apps.evaluator.src.infrastructure.evaluator_repository import (
    SQLAlchemyEvaluatorRepository,
)


class _StubEvaluatorRepository(SQLAlchemyEvaluatorRepository):
    def __init__(self, events: list[EvaluatorTraceEvent]) -> None:
        # DB is not used because load_events is overridden in tests.
        super().__init__(db=None)  # type: ignore[arg-type]
        self._events = events

    def load_events(self, input: EvaluatorTaskInput) -> list[EvaluatorTraceEvent]:
        return list(self._events)


def _make_task_input() -> EvaluatorTaskInput:
    return EvaluatorTaskInput(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        evaluator_version=1,
        start_event_index=0,
        end_event_index=5,
    )


def _make_event(
    *,
    session_id: UUID,
    event_type: str,
    event_index: int,
    lab_id: UUID | None = None,
    lab_version_id: UUID | None = None,
) -> EvaluatorTraceEvent:
    return EvaluatorTraceEvent(
        event_id=uuid4(),
        session_id=session_id,
        family="runtime",
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
        source="test",
        event_index=event_index,
        payload={},
        trace_version=1,
        correlation_id=None,
        request_id=None,
        actor_user_id=None,
        lab_id=lab_id,
        lab_version_id=lab_version_id,
    )


def test_evaluate_trace_window_no_op_when_no_rules_match() -> None:
    task = _make_task_input()
    events = [
        _make_event(
            session_id=task.session_id,
            event_type="SESSION_TRANSITIONED",
            event_index=0,
            lab_id=task.lab_id,
            lab_version_id=task.lab_version_id,
        ),
        _make_event(
            session_id=task.session_id,
            event_type="MODEL_TURN_COMPLETED",
            event_index=1,
            lab_id=task.lab_id,
            lab_version_id=task.lab_version_id,
        ),
    ]
    repo = _StubEvaluatorRepository(events=events)

    result = repo.evaluate_trace_window(input=task)

    assert result.evaluated_event_count == 2
    assert result.findings_count == 0
    assert result.no_op is True
    assert result.findings == ()


def test_evaluate_trace_window_produces_findings_for_matching_rules() -> None:
    task = _make_task_input()
    events = [
        _make_event(
            session_id=task.session_id,
            event_type="RUNTIME_PROVISION_FAILED",
            event_index=2,
            lab_id=task.lab_id,
            lab_version_id=task.lab_version_id,
        ),
        _make_event(
            session_id=task.session_id,
            event_type="MODEL_TURN_FAILED",
            event_index=3,
            lab_id=task.lab_id,
            lab_version_id=task.lab_version_id,
        ),
    ]
    repo = _StubEvaluatorRepository(events=events)

    result = repo.evaluate_trace_window(input=task)

    assert result.findings_count == 2
    assert result.no_op is False
    assert tuple(f.code for f in result.findings) == (
        "runtime.provision_failed",
        "model.turn_failed",
    )


def test_evaluate_trace_window_rejects_invalid_window() -> None:
    bad_task = EvaluatorTaskInput(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        evaluator_version=1,
        start_event_index=5,
        end_event_index=4,
    )
    repo = _StubEvaluatorRepository(events=[])

    with pytest.raises(ValueError, match="Invalid event window"):
        repo.evaluate_trace_window(input=bad_task)
