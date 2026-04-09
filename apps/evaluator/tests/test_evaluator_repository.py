from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from apps.evaluator.src.application.rules.registry import SUPPORTED_BUNDLES
from apps.evaluator.src.application.service import evaluate_trace_window_once
from apps.evaluator.src.application.types import (
    EvaluatorFinding,
    EvaluatorRunResult,
    EvaluatorLabRuntimeBinding,
    EvaluatorTaskInput,
    EvaluatorTraceEvent,
)
from apps.evaluator.src.infrastructure.evaluator_repository import (
    SQLAlchemyEvaluatorRepository,
)

DEFAULT_SUPPORTED_TUPLE = next(iter(SUPPORTED_BUNDLES))


class _StubEvaluatorRepository(SQLAlchemyEvaluatorRepository):
    def __init__(self, events: list[EvaluatorTraceEvent]) -> None:
        # DB is not used because load_events is overridden in tests.
        super().__init__(db=None)  # type: ignore[arg-type]
        self._events = events

    def load_events(self, input: EvaluatorTaskInput) -> list[EvaluatorTraceEvent]:
        _ = input
        return list(self._events)

    def persist_result_if_new(
        self,
        idempo_key: str,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        lab_difficulty: str,
        evaluator_version: int,
        finding: EvaluatorFinding,
    ) -> bool:
        _ = (
            idempo_key,
            session_id,
            lab_id,
            lab_version_id,
            lab_difficulty,
            evaluator_version,
            finding,
        )
        return True


class _StubLabLookupRepo:
    def get_runtime_binding(
        self, lab_id: UUID, lab_version_id: UUID
    ) -> EvaluatorLabRuntimeBinding:
        _ = (lab_id, lab_version_id)
        return EvaluatorLabRuntimeBinding(
            lab_slug=DEFAULT_SUPPORTED_TUPLE[0],
            lab_version=DEFAULT_SUPPORTED_TUPLE[1],
        )


def _make_task_input() -> EvaluatorTaskInput:
    return EvaluatorTaskInput(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        lab_difficulty="medium",
        evaluator_version=DEFAULT_SUPPORTED_TUPLE[2],
        start_event_index=0,
        end_event_index=5,
    )


def _make_event(
    *,
    session_id: UUID,
    event_type: str,
    event_index: int,
    payload: dict[str, object] | None = None,
    family: str = "runtime",
    lab_id: UUID | None = None,
    lab_version_id: UUID | None = None,
) -> EvaluatorTraceEvent:
    return EvaluatorTraceEvent(
        event_id=uuid4(),
        session_id=session_id,
        family=family,
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
        source="test",
        event_index=event_index,
        payload=payload or {},
        trace_version=1,
        correlation_id=None,
        request_id=None,
        actor_user_id=None,
        lab_id=lab_id,
        lab_version_id=lab_version_id,
        lab_difficulty=None,
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

    result: EvaluatorRunResult = evaluate_trace_window_once(
        task=task, repo=repo, lab_lookup_repo=_StubLabLookupRepo()
    )

    assert result.evaluated_event_count == 2
    assert result.findings_count == 0
    assert result.no_op is True
    assert result.findings == ()


def test_evaluate_trace_window_produces_findings_for_matching_rules() -> None:
    task = _make_task_input()
    events = [
        _make_event(
            session_id=task.session_id,
            event_type="MALICIOUS_EMAIL_READ",
            event_index=2,
            payload={
                "email_id": "e2",
                "subject": "URGENT: Policy update",
                "malicious_marker": True,
            },
            family="runtime",
            lab_id=task.lab_id,
            lab_version_id=task.lab_version_id,
        ),
        _make_event(
            session_id=task.session_id,
            event_type="TOKEN_DISCLOSED",
            event_index=3,
            payload={
                "channel": "assistant_output",
                "token_kind": "simulated_lab_token",
            },
            family="runtime",
            lab_id=task.lab_id,
            lab_version_id=task.lab_version_id,
        ),
    ]
    repo = _StubEvaluatorRepository(events=events)

    result = evaluate_trace_window_once(
        task=task, repo=repo, lab_lookup_repo=_StubLabLookupRepo()
    )

    assert result.findings_count == 3
    assert result.no_op is False
    assert tuple(f.code for f in result.findings) == (
        "pi.global.inbox_interaction_triggered",
        "pi.global.malicious_artifact_entered_context",
        "pi.medium.token_exposed",
    )


def test_evaluate_trace_window_rejects_invalid_window() -> None:
    bad_task = EvaluatorTaskInput(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        lab_difficulty="medium",
        evaluator_version=1,
        start_event_index=5,
        end_event_index=4,
    )
    repo = _StubEvaluatorRepository(events=[])

    with pytest.raises(ValueError, match="Invalid event window"):
        evaluate_trace_window_once(
            task=bad_task, repo=repo, lab_lookup_repo=_StubLabLookupRepo()
        )
