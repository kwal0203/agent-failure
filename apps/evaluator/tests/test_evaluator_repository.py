from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from apps.contracts.src.lab_secrets import LAB1_DISCLOSED_SECRET_KIND
from apps.evaluator.src.application.rules.registry import SUPPORTED_BUNDLES
from apps.evaluator.src.application.service import evaluate_trace_window_once
from apps.evaluator.src.application.types import (
    EvaluatorFinding,
    EvaluatorRunResult,
    EvaluatorLabRuntimeBinding,
    EvaluatorTaskInput,
    EvaluatorTraceEvent,
    ExplanationSignal,
    LearnerExplanation,
    PendingEvaluatorEvent,
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
        self.explanations_loaded = False

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

    def list_explanations_for_session(
        self, session_id: UUID
    ) -> tuple[LearnerExplanation, ...]:
        _ = session_id
        self.explanations_loaded = True
        return ()


class _StubLabLookupRepo:
    def get_runtime_binding(
        self, lab_id: UUID, lab_version_id: UUID
    ) -> EvaluatorLabRuntimeBinding:
        _ = (lab_id, lab_version_id)
        return EvaluatorLabRuntimeBinding(
            lab_slug=DEFAULT_SUPPORTED_TUPLE[0],
            lab_version=DEFAULT_SUPPORTED_TUPLE[1],
        )


class _StubClassifier:
    def __init__(self) -> None:
        self.called = False

    def classify(
        self, explanations: tuple[LearnerExplanation, ...], *, lab_difficulty: str
    ) -> tuple[ExplanationSignal, ...]:
        _ = (explanations, lab_difficulty)
        self.called = True
        return ()


class _StubOutboxRepo:
    def claim_pending_evaluate(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingEvaluatorEvent]:
        _ = (limit, now)
        return []

    def mark_processed(
        self, *, outbox_event_id: UUID, processed_at: datetime | None = None
    ) -> None:
        _ = (outbox_event_id, processed_at)

    def mark_terminal_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        failed_at: datetime | None = None,
    ) -> None:
        _ = (outbox_event_id, error_message, failed_at)

    def enqueue_learner_feedback_publish_request(
        self, *, session_id: UUID, requested_at: datetime | None = None
    ) -> None:
        _ = (session_id, requested_at)

    def enqueue_objective_completed_event(self, *, event: object) -> None:
        _ = event

    def enqueue_session_feedback_created_event(self, *, event: object) -> None:
        _ = event


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
    classifier = _StubClassifier()

    result: EvaluatorRunResult = evaluate_trace_window_once(
        task=task,
        repo=repo,
        lab_lookup_repo=_StubLabLookupRepo(),
        outbox_repo=_StubOutboxRepo(),
        classifier=classifier,
    )

    assert result.evaluated_event_count == 2
    assert result.findings_count == 0
    assert result.no_op is True
    assert result.findings == ()
    assert repo.explanations_loaded is True
    assert classifier.called is True


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
                "token_kind": LAB1_DISCLOSED_SECRET_KIND,
            },
            family="runtime",
            lab_id=task.lab_id,
            lab_version_id=task.lab_version_id,
        ),
    ]
    repo = _StubEvaluatorRepository(events=events)
    classifier = _StubClassifier()

    result = evaluate_trace_window_once(
        task=task,
        repo=repo,
        lab_lookup_repo=_StubLabLookupRepo(),
        outbox_repo=_StubOutboxRepo(),
        classifier=classifier,
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
    classifier = _StubClassifier()

    with pytest.raises(ValueError, match="Invalid event window"):
        evaluate_trace_window_once(
            task=bad_task,
            repo=repo,
            lab_lookup_repo=_StubLabLookupRepo(),
            outbox_repo=_StubOutboxRepo(),
            classifier=classifier,
        )
