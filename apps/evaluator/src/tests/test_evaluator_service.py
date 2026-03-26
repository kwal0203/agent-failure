from dataclasses import dataclass
from uuid import uuid4

import pytest

from apps.evaluator.src.application.service import evaluate_trace_window_once
from apps.evaluator.src.application.types import (
    EvaluatorFinding,
    EvaluatorRunResult,
    EvaluatorTaskInput,
)


@dataclass
class _FakeRepo:
    result: EvaluatorRunResult

    def evaluate_trace_window(self, input: EvaluatorTaskInput) -> EvaluatorRunResult:
        _ = input
        return self.result


class _RaisingRepo:
    def evaluate_trace_window(self, input: EvaluatorTaskInput) -> EvaluatorRunResult:
        _ = input
        raise RuntimeError("boom")


def _make_task() -> EvaluatorTaskInput:
    return EvaluatorTaskInput(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        evaluator_version=1,
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


def test_evaluate_trace_window_once_returns_repo_result() -> None:
    task = _make_task()
    expected = _make_result(task, no_op=False)
    repo = _FakeRepo(result=expected)

    result = evaluate_trace_window_once(task=task, repo=repo)

    assert result == expected


def test_evaluate_trace_window_once_logs_and_reraises_repo_exception(
    caplog: pytest.LogCaptureFixture,
) -> None:
    task = _make_task()
    repo = _RaisingRepo()

    with pytest.raises(RuntimeError, match="boom"):
        evaluate_trace_window_once(task=task, repo=repo)

    assert any("evaluator.run.failed" in rec.message for rec in caplog.records)
