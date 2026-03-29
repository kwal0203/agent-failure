from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import cast
from uuid import UUID, uuid4

import pytest

from apps.evaluator.src.application import service
from apps.evaluator.src.application.rules.registry import SUPPORTED_BUNDLE_KEY
from apps.evaluator.src.application.service import (
    process_evaluate_pending_once,
    get_learner_feedback,
)
from apps.evaluator.src.application.types import (
    EvaluatorFinding,
    EvaluatorLabRuntimeBinding,
    EvaluatorOnceResult,
    PendingEvaluatorEvent,
    EvaluatorPersistedResult,
    ResultType,
    EvaluatorTaskInput,
    EvaluatorTraceEvent,
)


@dataclass
class _FakeRepo:
    events: list[EvaluatorTraceEvent]
    persisted_calls: list[tuple[str, UUID, UUID, UUID, int, EvaluatorFinding]] = field(
        default_factory=list
    )
    persisted_results: list[EvaluatorPersistedResult] = field(default_factory=list)

    def load_events(self, input: EvaluatorTaskInput) -> list[EvaluatorTraceEvent]:
        _ = input
        return list(self.events)

    def persist_result_if_new(
        self,
        idempo_key: str,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        evaluator_version: int,
        finding: EvaluatorFinding,
    ) -> bool:
        self.persisted_calls.append(
            (
                idempo_key,
                session_id,
                lab_id,
                lab_version_id,
                evaluator_version,
                finding,
            )
        )
        return True

    def list_results_for_session(
        self, session_id: UUID
    ) -> list[EvaluatorPersistedResult]:
        _ = session_id
        return list(self.persisted_results)


class _RaisingRepo:
    def load_events(self, input: EvaluatorTaskInput) -> list[EvaluatorTraceEvent]:
        _ = input
        raise RuntimeError("boom")

    def persist_result_if_new(
        self,
        idempo_key: str,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        evaluator_version: int,
        finding: EvaluatorFinding,
    ) -> bool:
        _ = (
            idempo_key,
            session_id,
            lab_id,
            lab_version_id,
            evaluator_version,
            finding,
        )
        return True

    def list_results_for_session(
        self, session_id: UUID
    ) -> list[EvaluatorPersistedResult]:
        _ = session_id
        return []


class _StubLabLookupRepo:
    def get_runtime_binding(
        self, lab_id: UUID, lab_version_id: UUID
    ) -> EvaluatorLabRuntimeBinding:
        _ = (lab_id, lab_version_id)
        return EvaluatorLabRuntimeBinding(
            lab_slug=SUPPORTED_BUNDLE_KEY[0],
            lab_version=SUPPORTED_BUNDLE_KEY[1],
        )


def _make_task() -> EvaluatorTaskInput:
    return EvaluatorTaskInput(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        evaluator_version=SUPPORTED_BUNDLE_KEY[2],
        start_event_index=0,
        end_event_index=3,
    )


def _make_trace_event(
    task: EvaluatorTaskInput, *, event_index: int
) -> EvaluatorTraceEvent:
    return EvaluatorTraceEvent(
        event_id=uuid4(),
        session_id=task.session_id,
        family="model",
        event_type="MODEL_TURN_COMPLETED",
        occurred_at=datetime.now(timezone.utc),
        source="test",
        event_index=event_index,
        payload={},
        trace_version=1,
        correlation_id=None,
        request_id=None,
        actor_user_id=None,
        lab_id=task.lab_id,
        lab_version_id=task.lab_version_id,
    )


class _FakeOutboxRepo:
    def __init__(self, pending: list[PendingEvaluatorEvent]) -> None:
        self.pending = pending
        self.processed: list[UUID] = []
        self.failed: list[tuple[UUID, str]] = []
        self.enqueued_feedback_requests: list[tuple[UUID, datetime | None]] = []

    def claim_pending_evaluate(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingEvaluatorEvent]:
        _ = (limit, now)
        return list(self.pending)

    def mark_processed(
        self, *, outbox_event_id: UUID, processed_at: datetime | None = None
    ) -> None:
        _ = processed_at
        self.processed.append(outbox_event_id)

    def mark_terminal_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        failed_at: datetime | None = None,
    ) -> None:
        _ = failed_at
        self.failed.append((outbox_event_id, error_message))

    def enqueue_learner_feedback_publish_request(
        self, *, session_id: UUID, requested_at: datetime | None = None
    ) -> None:
        self.enqueued_feedback_requests.append((session_id, requested_at))


def _make_persisted_result(
    task: EvaluatorTaskInput,
    *,
    result_type: ResultType,
    code: str,
    reason_code: str = "REASON",
    feedback_payload: dict[str, object] | None = None,
) -> EvaluatorPersistedResult:
    return EvaluatorPersistedResult(
        id=uuid4(),
        idempotency_key=f"idempo:{uuid4()}",
        result_type=result_type,
        code=code,
        trigger_event_index=1,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="flag",
        reason_code=reason_code,
        feedback_payload=feedback_payload or {},
        created_at=datetime.now(timezone.utc),
        session_id=task.session_id,
        lab_id=task.lab_id,
        lab_version_id=task.lab_version_id,
        evaluator_version=task.evaluator_version,
    )


def test_process_evaluate_pending_once_returns_stats_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _make_task()
    repo = _FakeRepo(events=[_make_trace_event(task, event_index=0)])
    outbox_event_id = uuid4()
    outbox_repo = _FakeOutboxRepo(
        pending=[
            PendingEvaluatorEvent(
                outbox_event_id=outbox_event_id,
                task=task,
                attempt_count=1,
            )
        ]
    )
    expected_findings = (
        EvaluatorFinding(
            result_type="constraint_violation",
            code="runtime.provision_failed",
            trigger_event_index=1,
            trigger_start_event_index=None,
            trigger_end_event_index=None,
            feedback_level="flag",
            reason_code="RUNTIME_PROVISION_FAILED",
            feedback_payload={"event_type": "RUNTIME_PROVISION_FAILED"},
        ),
    )

    class _FakeBundle:
        def run(
            self, events: list[EvaluatorTraceEvent]
        ) -> tuple[EvaluatorFinding, ...]:
            _ = events
            return expected_findings

    monkeypatch.setattr(
        service, "resolve_bundle", lambda *, binding, task: _FakeBundle()
    )

    result = process_evaluate_pending_once(
        repo=repo, lab_lookup_repo=_StubLabLookupRepo(), outbox_repo=outbox_repo
    )

    assert result == EvaluatorOnceResult(
        claimed_count=1,
        succeeded_count=1,
        failed_count=0,
        retried_count=0,
    )
    assert len(repo.persisted_calls) == 1
    assert outbox_repo.processed == [outbox_event_id]
    assert outbox_repo.failed == []
    assert len(outbox_repo.enqueued_feedback_requests) == 1
    assert outbox_repo.enqueued_feedback_requests[0][0] == task.session_id


def test_process_evaluate_pending_once_does_not_enqueue_feedback_publish_when_no_new_findings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _make_task()
    repo = _FakeRepo(events=[_make_trace_event(task, event_index=0)])
    outbox_event_id = uuid4()
    outbox_repo = _FakeOutboxRepo(
        pending=[
            PendingEvaluatorEvent(
                outbox_event_id=outbox_event_id,
                task=task,
                attempt_count=1,
            )
        ]
    )

    class _FakeBundle:
        def run(
            self, events: list[EvaluatorTraceEvent]
        ) -> tuple[EvaluatorFinding, ...]:
            _ = events
            return ()

    monkeypatch.setattr(
        service, "resolve_bundle", lambda *, binding, task: _FakeBundle()
    )

    result = process_evaluate_pending_once(
        repo=repo, lab_lookup_repo=_StubLabLookupRepo(), outbox_repo=outbox_repo
    )

    assert result == EvaluatorOnceResult(
        claimed_count=1,
        succeeded_count=1,
        failed_count=0,
        retried_count=0,
    )
    assert outbox_repo.processed == [outbox_event_id]
    assert outbox_repo.failed == []
    assert outbox_repo.enqueued_feedback_requests == []


def test_process_evaluate_pending_once_marks_failure_and_logs_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    task = _make_task()
    repo = _RaisingRepo()
    outbox_event_id = uuid4()
    outbox_repo = _FakeOutboxRepo(
        pending=[
            PendingEvaluatorEvent(
                outbox_event_id=outbox_event_id,
                task=task,
                attempt_count=1,
            )
        ]
    )

    result = process_evaluate_pending_once(
        repo=repo, lab_lookup_repo=_StubLabLookupRepo(), outbox_repo=outbox_repo
    )

    assert result == EvaluatorOnceResult(
        claimed_count=1,
        succeeded_count=0,
        failed_count=1,
        retried_count=0,
    )
    assert outbox_repo.processed == []
    assert len(outbox_repo.failed) == 1
    assert outbox_repo.failed[0][0] == outbox_event_id
    assert any("evaluator.run.failed" in rec.message for rec in caplog.records)


@pytest.mark.parametrize(
    ("result_type", "expected_status"),
    [
        ("constraint_violation", "learned"),
        ("success_signal", "learned"),
        ("partial_success", "progress"),
        ("no_effect", "no_progress"),
        ("terminal_outcome", "session_terminal"),
    ],
)
def test_get_learner_feedback_maps_status_from_result_type(
    result_type: ResultType, expected_status: str
) -> None:
    task = _make_task()
    repo = _FakeRepo(
        events=[],
        persisted_results=[
            _make_persisted_result(
                task,
                result_type=result_type,
                code="pi.attack_attempt_blocked",
            )
        ],
    )

    feedback = get_learner_feedback(session_id=task.session_id, repo=repo)

    assert len(feedback) == 1
    assert feedback[0].status == expected_status


def test_get_learner_feedback_projects_evidence_snippet_by_code() -> None:
    task = _make_task()
    repo = _FakeRepo(
        events=[],
        persisted_results=[
            _make_persisted_result(
                task,
                result_type="constraint_violation",
                code="pi.secret_exfiltration_success",
                feedback_payload={"matched_value": "FLAG{test-secret}"},
            ),
            _make_persisted_result(
                task,
                result_type="constraint_violation",
                code="pi.protected_tool_access_violation",
                feedback_payload={
                    "tool_name": "fs.read",
                    "target_resource": "/protected/flag.txt",
                },
            ),
            _make_persisted_result(
                task,
                result_type="partial_success",
                code="pi.attack_attempt_blocked",
                feedback_payload={
                    "blocked_by": "model_policy",
                    "block_reason_code": "POLICY_DENIED",
                },
            ),
        ],
    )

    feedback = get_learner_feedback(session_id=task.session_id, repo=repo)

    assert feedback[0].evidence_snippet == "FLAG{test-secret}"
    assert (
        feedback[1].evidence_snippet
        == "fs.read accessed protected resource /protected/flag.txt."
    )
    assert (
        feedback[2].evidence_snippet
        == "Attack attempt blocked by model_policy (POLICY_DENIED)"
    )


def test_get_learner_feedback_raises_on_unknown_result_type() -> None:
    task = _make_task()
    repo = _FakeRepo(
        events=[],
        persisted_results=[
            _make_persisted_result(
                task,
                result_type=cast(ResultType, "unknown_type"),
                code="pi.attack_attempt_blocked",
            )
        ],
    )

    with pytest.raises(ValueError, match="Unsupported result_type: unknown_type"):
        get_learner_feedback(session_id=task.session_id, repo=repo)
