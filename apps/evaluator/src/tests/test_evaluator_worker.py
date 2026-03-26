from uuid import uuid4
from typing import Literal

from pytest import MonkeyPatch

from apps.evaluator.src.application.types import (
    EvaluatorFinding,
    EvaluatorRunResult,
    EvaluatorTaskInput,
)
from apps.evaluator.src.interfaces.runtime import evaluator_worker


def _make_task() -> EvaluatorTaskInput:
    return EvaluatorTaskInput(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        evaluator_version=1,
        start_event_index=0,
        end_event_index=2,
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
        evaluated_event_count=3,
        findings_count=findings_count,
        no_op=no_op,
        findings=findings,
    )


class _FakeSessionFactory:
    def __enter__(self) -> object:
        return object()

    def __exit__(self, exc_type: object, exc: object, tb: object) -> Literal[False]:
        _ = (exc_type, exc, tb)
        return False


def test_run_once_invokes_service_and_returns_result(monkeypatch: MonkeyPatch) -> None:
    task = _make_task()
    expected = _make_result(task, no_op=False)
    calls: dict[str, object] = {}

    class _FakeRepo:
        def __init__(self, db: object) -> None:
            calls["db"] = db

    def _fake_eval_once(
        *, task: EvaluatorTaskInput, repo: object
    ) -> EvaluatorRunResult:
        calls["task"] = task
        calls["repo"] = repo
        return expected

    monkeypatch.setattr(evaluator_worker, "SessionFactory", _FakeSessionFactory)
    monkeypatch.setattr(evaluator_worker, "SQLAlchemyEvaluatorRepository", _FakeRepo)
    monkeypatch.setattr(evaluator_worker, "evaluate_trace_window_once", _fake_eval_once)

    result = evaluator_worker.run_once(task=task)

    assert result == expected
    assert calls["task"] == task
    assert calls["repo"].__class__ is _FakeRepo
    assert "db" in calls


def test_run_once_propagates_no_op_result(monkeypatch: MonkeyPatch) -> None:
    task = _make_task()
    expected = _make_result(task, no_op=True)

    class _FakeRepo:
        def __init__(self, db: object) -> None:
            _ = db

    def _fake_eval_once(
        *, task: EvaluatorTaskInput, repo: object
    ) -> EvaluatorRunResult:
        _ = (task, repo)
        return expected

    monkeypatch.setattr(evaluator_worker, "SessionFactory", _FakeSessionFactory)
    monkeypatch.setattr(evaluator_worker, "SQLAlchemyEvaluatorRepository", _FakeRepo)
    monkeypatch.setattr(evaluator_worker, "evaluate_trace_window_once", _fake_eval_once)

    result = evaluator_worker.run_once(task=task)

    assert result.no_op is True
    assert result.findings_count == 0
    assert result.findings == ()
