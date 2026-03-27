from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from apps.evaluator.src.application import service
from apps.evaluator.src.application.rules.registry import SUPPORTED_BUNDLE_KEY
from apps.evaluator.src.application.service import evaluate_trace_window_once
from apps.evaluator.src.application.types import (
    EvaluatorFinding,
    EvaluatorLabRuntimeBinding,
    EvaluatorRunResult,
    EvaluatorTaskInput,
    EvaluatorTraceEvent,
)


@dataclass
class _FakeRepo:
    events: list[EvaluatorTraceEvent]
    persisted_calls: list[tuple[str, UUID, UUID, UUID, int, EvaluatorFinding]] = field(
        default_factory=list
    )

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


def _make_result(task: EvaluatorTaskInput, *, no_op: bool) -> EvaluatorRunResult:
    findings: tuple[EvaluatorFinding, ...] = ()
    findings_count = 0
    if not no_op:
        findings = (
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
        findings_count = 1

    return EvaluatorRunResult(
        session_id=task.session_id,
        lab_id=task.lab_id,
        lab_version_id=task.lab_version_id,
        evaluator_version=task.evaluator_version,
        start_event_index=task.start_event_index,
        end_event_index=task.end_event_index,
        evaluated_event_count=4,
        findings_count=findings_count,
        no_op=no_op,
        findings=findings,
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


def test_evaluate_trace_window_once_returns_repo_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _make_task()
    expected = _make_result(task, no_op=False)
    repo = _FakeRepo(events=[_make_trace_event(task, event_index=0)])

    class _FakeBundle:
        def run(
            self, events: list[EvaluatorTraceEvent]
        ) -> tuple[EvaluatorFinding, ...]:
            _ = events
            return expected.findings

    monkeypatch.setattr(
        service, "resolve_bundle", lambda *, binding, task: _FakeBundle()
    )

    result = evaluate_trace_window_once(
        task=task, repo=repo, lab_lookup_repo=_StubLabLookupRepo()
    )

    assert result.findings == expected.findings
    assert result.findings_count == expected.findings_count
    assert len(repo.persisted_calls) == expected.findings_count


def test_evaluate_trace_window_once_logs_and_reraises_repo_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    task = _make_task()
    repo = _RaisingRepo()

    with pytest.raises(RuntimeError, match="boom"):
        evaluate_trace_window_once(
            task=task, repo=repo, lab_lookup_repo=_StubLabLookupRepo()
        )

    assert any("evaluator.run.failed" in rec.message for rec in caplog.records)
