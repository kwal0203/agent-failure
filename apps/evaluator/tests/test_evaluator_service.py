from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import cast
from uuid import UUID, uuid4

import pytest

from apps.evaluator.src.application import service
from apps.evaluator.src.application.rules.contract import (
    REASON_CODE_MP_FEEDBACK_REQUESTED_ACCOUNT_MISMATCH_CANONICAL,
    REASON_CODE_MP_FEEDBACK_SUCCESSFUL_INVOICE_PAYMENT,
    REASON_CODE_MP_FEEDBACK_VENDOR_PROFILE_MEMORY_WRITE_BLOCKED,
    REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS,
    REASON_CODE_PI_MALICIOUS_EMAIL_READ_NO_DISCLOSURE,
    REASON_CODE_PI_MALICIOUS_EMAIL_NOT_READ_YET,
    REASON_CODE_TLM_FEEDBACK_MANUAL_DB_DELETE_ATTEMPT,
    REASON_CODE_TLM_FEEDBACK_AUTHORITY_BULLETIN_REJECTED,
    REASON_CODE_TLM_FEEDBACK_NON_DESTRUCTIVE_RUNBOOK_UPDATE,
    REASON_CODE_TLM_FEEDBACK_QUALIFYING_LOG_NO_DB_DELETE,
    RULE_ID_PI_SECRET_EXFIL,
)
from apps.evaluator.src.application.rules.registry import SUPPORTED_BUNDLES
from apps.evaluator.src.application.idempotency import (
    build_feedback_event_idempotency_key,
    build_objective_event_idempotency_key,
)
from apps.evaluator.src.application.service import (
    process_evaluate_pending_once,
    get_learner_feedback,
)
from apps.evaluator.src.application.types import (
    EvaluatorFinding,
    EvaluatorLabRuntimeBinding,
    EvaluatorOnceResult,
    ObjectiveCompletedEvent,
    SessionFeedbackCreatedEvent,
    PendingEvaluatorEvent,
    EvaluatorPersistedResult,
    ResultType,
    EvaluatorTaskInput,
    EvaluatorTraceEvent,
    ExplanationSignal,
    LearnerExplanation,
)

DEFAULT_SUPPORTED_TUPLE = next(iter(SUPPORTED_BUNDLES))


@dataclass
class _FakeRepo:
    events: list[EvaluatorTraceEvent]
    persisted_calls: list[tuple[str, UUID, UUID, UUID, str, int, EvaluatorFinding]] = (
        field(default_factory=list)
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
        lab_difficulty: str,
        evaluator_version: int,
        finding: EvaluatorFinding,
    ) -> bool:
        self.persisted_calls.append(
            (
                idempo_key,
                session_id,
                lab_id,
                lab_version_id,
                lab_difficulty,
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

    def list_explanations_for_session(
        self, session_id: UUID
    ) -> tuple[LearnerExplanation, ...]:
        _ = session_id
        return ()


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

    def list_results_for_session(
        self, session_id: UUID
    ) -> list[EvaluatorPersistedResult]:
        _ = session_id
        return []

    def list_explanations_for_session(
        self, session_id: UUID
    ) -> tuple[LearnerExplanation, ...]:
        _ = session_id
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


class _StubLab1LookupRepo:
    def get_runtime_binding(
        self, lab_id: UUID, lab_version_id: UUID
    ) -> EvaluatorLabRuntimeBinding:
        _ = (lab_id, lab_version_id)
        return EvaluatorLabRuntimeBinding(
            lab_slug="prompt-injection",
            lab_version="v1",
        )


class _FakeClassifier:
    def classify(
        self, explanations: tuple[LearnerExplanation, ...], *, lab_difficulty: str
    ) -> tuple[ExplanationSignal, ...]:
        _ = (explanations, lab_difficulty)
        return ()


def _make_task() -> EvaluatorTaskInput:
    return EvaluatorTaskInput(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        lab_difficulty="medium",
        evaluator_version=DEFAULT_SUPPORTED_TUPLE[2],
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
        lab_difficulty=None,
    )


class _FakeOutboxRepo:
    def __init__(self, pending: list[PendingEvaluatorEvent]) -> None:
        self.pending = pending
        self.processed: list[UUID] = []
        self.failed: list[tuple[UUID, str]] = []
        self.enqueued_feedback_requests: list[tuple[UUID, datetime | None]] = []
        self.objective_events_enqueued = 0
        self.objective_events: list[ObjectiveCompletedEvent] = []
        self.feedback_events_enqueued = 0
        self.feedback_events: list[SessionFeedbackCreatedEvent] = []

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

    def enqueue_objective_completed_event(
        self, *, event: ObjectiveCompletedEvent
    ) -> None:
        self.objective_events.append(event)
        self.objective_events_enqueued += 1

    def enqueue_session_feedback_created_event(
        self, *, event: SessionFeedbackCreatedEvent
    ) -> None:
        self.feedback_events.append(event)
        self.feedback_events_enqueued += 1


class _IdempotentObjectiveOutboxRepo(_FakeOutboxRepo):
    def __init__(self, pending: list[PendingEvaluatorEvent]) -> None:
        super().__init__(pending=pending)
        self._objective_idempotency_keys_seen: set[str] = set()

    def enqueue_objective_completed_event(
        self, *, event: ObjectiveCompletedEvent
    ) -> None:
        if event.idempotency_key in self._objective_idempotency_keys_seen:
            return
        self._objective_idempotency_keys_seen.add(event.idempotency_key)
        self.objective_events.append(event)
        self.objective_events_enqueued += 1

    def enqueue_session_feedback_created_event(
        self, *, event: SessionFeedbackCreatedEvent
    ) -> None:
        if not hasattr(self, "_feedback_idempotency_keys_seen"):
            self._feedback_idempotency_keys_seen: set[str] = set()
        if event.idempotency_key in self._feedback_idempotency_keys_seen:
            return
        self._feedback_idempotency_keys_seen.add(event.idempotency_key)
        self.feedback_events.append(event)
        self.feedback_events_enqueued += 1


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
            self,
            events: list[EvaluatorTraceEvent],
            explanation_signals: tuple[ExplanationSignal, ...],
        ) -> tuple[EvaluatorFinding, ...]:
            _ = (events, explanation_signals)
            return expected_findings

    monkeypatch.setattr(
        service, "resolve_bundle", lambda *, binding, task: _FakeBundle()
    )

    result = process_evaluate_pending_once(
        repo=repo,
        lab_lookup_repo=_StubLabLookupRepo(),
        outbox_repo=outbox_repo,
        classifier=_FakeClassifier(),
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
            self,
            events: list[EvaluatorTraceEvent],
            explanation_signals: tuple[ExplanationSignal, ...],
        ) -> tuple[EvaluatorFinding, ...]:
            _ = (events, explanation_signals)
            return ()

    monkeypatch.setattr(
        service, "resolve_bundle", lambda *, binding, task: _FakeBundle()
    )

    result = process_evaluate_pending_once(
        repo=repo,
        lab_lookup_repo=_StubLabLookupRepo(),
        outbox_repo=outbox_repo,
        classifier=_FakeClassifier(),
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
        repo=repo,
        lab_lookup_repo=_StubLabLookupRepo(),
        outbox_repo=outbox_repo,
        classifier=_FakeClassifier(),
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
    assert any("evaluator run failed" in rec.message for rec in caplog.records)


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
                code=RULE_ID_PI_SECRET_EXFIL,
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


def test_map_finding_to_feedback_maps_supported_reason_code() -> None:
    finding = EvaluatorFinding(
        result_type="no_effect",
        code="pi.benign_email_injected_no_progress",
        trigger_event_index=1,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code=REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS,
        feedback_payload={},
    )

    mapped = service._map_finding_to_feedback(finding)

    assert mapped is not None
    assert mapped.feedback_key == "lab1_benign_email_not_progressing"
    assert mapped.severity == "info"
    assert mapped.reason_code == REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS


def test_map_finding_to_feedback_maps_malicious_email_not_read_yet_reason_code() -> (
    None
):
    finding = EvaluatorFinding(
        result_type="no_effect",
        code="pi.malicious_email_not_read_yet",
        trigger_event_index=3,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code=REASON_CODE_PI_MALICIOUS_EMAIL_NOT_READ_YET,
        feedback_payload={},
    )

    mapped = service._map_finding_to_feedback(finding)

    assert mapped is not None
    assert mapped.feedback_key == "lab1_malicious_email_not_read_yet"
    assert mapped.severity == "warning"
    assert mapped.reason_code == REASON_CODE_PI_MALICIOUS_EMAIL_NOT_READ_YET


def test_map_finding_to_feedback_maps_malicious_email_read_no_disclosure_reason_code() -> (
    None
):
    finding = EvaluatorFinding(
        result_type="no_effect",
        code="pi.malicious_email_read_no_disclosure",
        trigger_event_index=4,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code=REASON_CODE_PI_MALICIOUS_EMAIL_READ_NO_DISCLOSURE,
        feedback_payload={},
    )

    mapped = service._map_finding_to_feedback(finding)

    assert mapped is not None
    assert mapped.feedback_key == "lab1_malicious_email_read_no_disclosure"
    assert mapped.severity == "warning"
    assert mapped.reason_code == REASON_CODE_PI_MALICIOUS_EMAIL_READ_NO_DISCLOSURE


def test_map_finding_to_feedback_returns_none_for_unsupported_reason_code() -> None:
    finding = EvaluatorFinding(
        result_type="no_effect",
        code="pi.some_other_rule",
        trigger_event_index=1,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code="PI_SOME_OTHER_REASON",
        feedback_payload={},
    )

    assert service._map_finding_to_feedback(finding) is None


def test_map_finding_to_feedback_maps_lab2_bulletin_rejected_reason_code() -> None:
    finding = EvaluatorFinding(
        result_type="no_effect",
        code="tm.authority_bulletin_rejected",
        trigger_event_index=6,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code=REASON_CODE_TLM_FEEDBACK_AUTHORITY_BULLETIN_REJECTED,
        feedback_payload={},
    )

    mapped = service._map_finding_to_feedback(finding)

    assert mapped is not None
    assert mapped.feedback_key == "lab2_authority_bulletin_rejected"
    assert mapped.severity == "warning"
    assert mapped.reason_code == REASON_CODE_TLM_FEEDBACK_AUTHORITY_BULLETIN_REJECTED


def test_map_finding_to_feedback_maps_lab2_non_destructive_runbook_reason_code() -> (
    None
):
    finding = EvaluatorFinding(
        result_type="no_effect",
        code="tm.runbook_altered_not_destructive",
        trigger_event_index=7,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code=REASON_CODE_TLM_FEEDBACK_NON_DESTRUCTIVE_RUNBOOK_UPDATE,
        feedback_payload={},
    )

    mapped = service._map_finding_to_feedback(finding)

    assert mapped is not None
    assert mapped.feedback_key == "lab2_runbook_altered_not_destructive"
    assert mapped.severity == "info"
    assert mapped.reason_code == REASON_CODE_TLM_FEEDBACK_NON_DESTRUCTIVE_RUNBOOK_UPDATE


def test_map_finding_to_feedback_maps_lab2_qualifying_log_without_delete_reason_code() -> (
    None
):
    finding = EvaluatorFinding(
        result_type="no_effect",
        code="tm.qualifying_log_without_delete",
        trigger_event_index=8,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code=REASON_CODE_TLM_FEEDBACK_QUALIFYING_LOG_NO_DB_DELETE,
        feedback_payload={},
    )

    mapped = service._map_finding_to_feedback(finding)

    assert mapped is not None
    assert mapped.feedback_key == "lab2_qualifying_log_without_delete"
    assert mapped.severity == "warning"
    assert mapped.reason_code == REASON_CODE_TLM_FEEDBACK_QUALIFYING_LOG_NO_DB_DELETE


def test_map_finding_to_feedback_maps_lab2_manual_db_delete_attempt_reason_code() -> (
    None
):
    finding = EvaluatorFinding(
        result_type="no_effect",
        code="tm.manual_db_delete_attempt",
        trigger_event_index=9,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code=REASON_CODE_TLM_FEEDBACK_MANUAL_DB_DELETE_ATTEMPT,
        feedback_payload={},
    )

    mapped = service._map_finding_to_feedback(finding)

    assert mapped is not None
    assert mapped.feedback_key == "lab2_manual_db_delete_attempt"
    assert mapped.severity == "warning"
    assert mapped.reason_code == REASON_CODE_TLM_FEEDBACK_MANUAL_DB_DELETE_ATTEMPT


def test_map_finding_to_feedback_maps_lab3_requested_account_mismatch_reason_code() -> (
    None
):
    finding = EvaluatorFinding(
        result_type="no_effect",
        code="mp.requested_account_mismatch_canonical",
        trigger_event_index=10,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code=REASON_CODE_MP_FEEDBACK_REQUESTED_ACCOUNT_MISMATCH_CANONICAL,
        feedback_payload={},
    )

    mapped = service._map_finding_to_feedback(finding)

    assert mapped is not None
    assert mapped.feedback_key == "lab3_requested_account_mismatch_canonical"
    assert mapped.severity == "warning"
    assert (
        mapped.reason_code
        == REASON_CODE_MP_FEEDBACK_REQUESTED_ACCOUNT_MISMATCH_CANONICAL
    )


def test_map_finding_to_feedback_maps_lab3_successful_invoice_payment_reason_code() -> (
    None
):
    finding = EvaluatorFinding(
        result_type="no_effect",
        code="mp.successful_invoice_payment",
        trigger_event_index=11,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code=REASON_CODE_MP_FEEDBACK_SUCCESSFUL_INVOICE_PAYMENT,
        feedback_payload={},
    )

    mapped = service._map_finding_to_feedback(finding)

    assert mapped is not None
    assert mapped.feedback_key == "lab3_successful_invoice_payment"
    assert mapped.severity == "info"
    assert mapped.reason_code == REASON_CODE_MP_FEEDBACK_SUCCESSFUL_INVOICE_PAYMENT


def test_map_finding_to_feedback_maps_lab3_vendor_profile_memory_write_blocked_reason_code() -> (
    None
):
    finding = EvaluatorFinding(
        result_type="no_effect",
        code="mp.vendor_profile_memory_write_blocked",
        trigger_event_index=12,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code=REASON_CODE_MP_FEEDBACK_VENDOR_PROFILE_MEMORY_WRITE_BLOCKED,
        feedback_payload={},
    )

    mapped = service._map_finding_to_feedback(finding)

    assert mapped is not None
    assert mapped.feedback_key == "lab3_vendor_profile_memory_write_blocked"
    assert mapped.severity == "warning"
    assert (
        mapped.reason_code
        == REASON_CODE_MP_FEEDBACK_VENDOR_PROFILE_MEMORY_WRITE_BLOCKED
    )


def test_build_session_feedback_created_event_populates_payload_fields() -> None:
    task = _make_task()
    created_at = datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc)
    finding = EvaluatorFinding(
        result_type="no_effect",
        code="pi.benign_email_injected_no_progress",
        trigger_event_index=9,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code=REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS,
        feedback_payload={},
    )

    event = service._build_session_feedback_created_event(
        task=task,
        finding=finding,
        created_at=created_at,
    )

    assert event is not None
    assert event.session_id == task.session_id
    assert event.lab_id == task.lab_id
    assert event.lab_version_id == task.lab_version_id
    assert event.feedback_key == "lab1_benign_email_not_progressing"
    assert event.reason_code == REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS
    assert event.severity == "info"
    assert event.trigger_event_index == 9
    assert event.created_at == created_at
    assert event.idempotency_key == build_feedback_event_idempotency_key(
        session_id=task.session_id,
        feedback_key=event.feedback_key,
        reason_code=event.reason_code,
        trigger_event_index=9,
    )


def test_build_session_feedback_created_event_returns_none_when_unmapped() -> None:
    task = _make_task()
    finding = EvaluatorFinding(
        result_type="no_effect",
        code="pi.unknown_feedback",
        trigger_event_index=1,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code="PI_UNKNOWN_REASON",
        feedback_payload={},
    )

    assert (
        service._build_session_feedback_created_event(
            task=task,
            finding=finding,
            created_at=datetime.now(timezone.utc),
        )
        is None
    )


def test_process_evaluate_pending_once_explanation_signals_influence_rules(
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

    class _SignalClassifier:
        def classify(
            self, explanations: tuple[LearnerExplanation, ...], *, lab_difficulty: str
        ) -> tuple[ExplanationSignal, ...]:
            _ = (explanations, lab_difficulty)
            return (
                ExplanationSignal(
                    explanation_id=uuid4(), confidence=1.0, mentions_root_cause=True
                ),
            )

    class _FakeBundle:
        def run(
            self,
            events: list[EvaluatorTraceEvent],
            explanation_signals: tuple[ExplanationSignal, ...],
        ) -> tuple[EvaluatorFinding, ...]:
            _ = events
            if (
                not explanation_signals
                or not explanation_signals[0].mentions_root_cause
            ):
                return ()
            return (
                EvaluatorFinding(
                    result_type="partial_success",
                    code="pi.global.explanation.mentioned_root_cause",
                    trigger_event_index=None,
                    trigger_start_event_index=None,
                    trigger_end_event_index=None,
                    feedback_level="info",
                    reason_code="PI_GLOBAL_EXPLANATION_MENTIONED_ROOT_CAUSE",
                    feedback_payload={"confidence": explanation_signals[0].confidence},
                ),
            )

    monkeypatch.setattr(
        service, "resolve_bundle", lambda *, binding, task: _FakeBundle()
    )

    result = process_evaluate_pending_once(
        repo=repo,
        lab_lookup_repo=_StubLabLookupRepo(),
        outbox_repo=outbox_repo,
        classifier=_SignalClassifier(),
    )

    assert result.succeeded_count == 1
    assert len(repo.persisted_calls) == 1
    persisted_finding = repo.persisted_calls[0][-1]
    assert persisted_finding.code == "pi.global.explanation.mentioned_root_cause"


def test_evaluate_trace_window_once_maps_lab2_findings_to_objective_events(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _make_task()
    repo = _FakeRepo(events=[_make_trace_event(task, event_index=0)])
    outbox_repo = _FakeOutboxRepo(pending=[])
    expected_findings = (
        EvaluatorFinding(
            result_type="constraint_violation",
            code="tm.unsafe_tool_invocation_triggered",
            trigger_event_index=2,
            trigger_start_event_index=None,
            trigger_end_event_index=None,
            feedback_level="flag",
            reason_code="TLM_RUNBOOK_ALTERED",
            feedback_payload={},
        ),
        EvaluatorFinding(
            result_type="constraint_violation",
            code="tm.log_created",
            trigger_event_index=3,
            trigger_start_event_index=None,
            trigger_end_event_index=None,
            feedback_level="flag",
            reason_code="TLM_LOG_CREATED",
            feedback_payload={},
        ),
        EvaluatorFinding(
            result_type="terminal_outcome",
            code="tm.critical_file_deleted",
            trigger_event_index=4,
            trigger_start_event_index=None,
            trigger_end_event_index=None,
            feedback_level="flag",
            reason_code="TLM_CRITICAL_FILE_DELETED",
            feedback_payload={},
        ),
    )

    class _FakeBundle:
        def run(
            self,
            events: list[EvaluatorTraceEvent],
            explanation_signals: tuple[ExplanationSignal, ...],
        ) -> tuple[EvaluatorFinding, ...]:
            _ = (events, explanation_signals)
            return expected_findings

    monkeypatch.setattr(
        service, "resolve_bundle", lambda *, binding, task: _FakeBundle()
    )

    result = service.evaluate_trace_window_once(
        task=task,
        repo=repo,
        lab_lookup_repo=_StubLabLookupRepo(),
        outbox_repo=outbox_repo,
        classifier=_FakeClassifier(),
    )

    assert result.findings_count == 3
    assert outbox_repo.objective_events_enqueued == 3
    assert [event.objective_key for event in outbox_repo.objective_events] == [
        "unsafe_tool_invocation_triggered",
        "log_created",
        "critical_file_deleted",
    ]


def test_evaluate_trace_window_once_maps_malicious_vendor_memory_written_to_objective_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _make_task()
    repo = _FakeRepo(events=[_make_trace_event(task, event_index=0)])
    outbox_repo = _FakeOutboxRepo(pending=[])
    finding = EvaluatorFinding(
        result_type="constraint_violation",
        code="imp.malicious_vendor_memory_written",
        trigger_event_index=5,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="flag",
        reason_code="IMP_MALICIOUS_VENDOR_MEMORY_WRITTEN",
        feedback_payload={},
    )

    class _FakeBundle:
        def run(
            self,
            events: list[EvaluatorTraceEvent],
            explanation_signals: tuple[ExplanationSignal, ...],
        ) -> tuple[EvaluatorFinding, ...]:
            _ = (events, explanation_signals)
            return (finding,)

    monkeypatch.setattr(
        service, "resolve_bundle", lambda *, binding, task: _FakeBundle()
    )

    service.evaluate_trace_window_once(
        task=task,
        repo=repo,
        lab_lookup_repo=_StubLabLookupRepo(),
        outbox_repo=outbox_repo,
        classifier=_FakeClassifier(),
    )

    assert outbox_repo.objective_events_enqueued == 1
    event = outbox_repo.objective_events[0]
    assert event.objective_key == "malicious_vendor_memory_written"
    assert event.reason_code == "IMP_MALICIOUS_VENDOR_MEMORY_WRITTEN"
    assert event.trigger_event_index == 5
    assert event.idempotency_key == build_objective_event_idempotency_key(
        session_id=task.session_id,
        objective_key="malicious_vendor_memory_written",
        trigger_event_index=5,
    )


def test_evaluate_trace_window_once_enqueues_session_feedback_created_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _make_task()
    repo = _FakeRepo(events=[_make_trace_event(task, event_index=0)])
    outbox_repo = _FakeOutboxRepo(pending=[])
    finding = EvaluatorFinding(
        result_type="no_effect",
        code="pi.benign_email_injected_no_progress",
        trigger_event_index=11,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code=REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS,
        feedback_payload={},
    )

    class _FakeBundle:
        def run(
            self,
            events: list[EvaluatorTraceEvent],
            explanation_signals: tuple[ExplanationSignal, ...],
        ) -> tuple[EvaluatorFinding, ...]:
            _ = (events, explanation_signals)
            return (finding,)

    monkeypatch.setattr(
        service, "resolve_bundle", lambda *, binding, task: _FakeBundle()
    )

    service.evaluate_trace_window_once(
        task=task,
        repo=repo,
        lab_lookup_repo=_StubLabLookupRepo(),
        outbox_repo=outbox_repo,
        classifier=_FakeClassifier(),
    )

    assert outbox_repo.feedback_events_enqueued == 1
    event = outbox_repo.feedback_events[0]
    assert event.session_id == task.session_id
    assert event.lab_id == task.lab_id
    assert event.lab_version_id == task.lab_version_id
    assert event.feedback_key == "lab1_benign_email_not_progressing"
    assert event.reason_code == REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS
    assert event.severity == "info"
    assert event.trigger_event_index == 11
    assert event.idempotency_key == build_feedback_event_idempotency_key(
        session_id=task.session_id,
        feedback_key=event.feedback_key,
        reason_code=event.reason_code,
        trigger_event_index=11,
    )


def test_evaluate_trace_window_once_lab1_benign_email_emits_feedback_once() -> None:
    task = _make_task()
    benign_event = EvaluatorTraceEvent(
        event_id=uuid4(),
        session_id=task.session_id,
        family="learner",
        event_type="ATTACK_EMAIL_SENT",
        occurred_at=datetime.now(timezone.utc),
        source="test",
        event_index=12,
        payload={
            "email_id": "email-benign-1",
            "email_from": "billing@vendor.example",
            "subject": "Weekly status update",
            "malicious_marker": False,
        },
        trace_version=1,
        correlation_id=None,
        request_id=None,
        actor_user_id=None,
        lab_id=task.lab_id,
        lab_version_id=task.lab_version_id,
        lab_difficulty=None,
    )
    repo = _FakeRepo(events=[benign_event])
    outbox_repo = _FakeOutboxRepo(pending=[])

    service.evaluate_trace_window_once(
        task=task,
        repo=repo,
        lab_lookup_repo=_StubLab1LookupRepo(),
        outbox_repo=outbox_repo,
        classifier=_FakeClassifier(),
    )

    assert outbox_repo.feedback_events_enqueued == 1
    assert len(outbox_repo.feedback_events) == 1
    event = outbox_repo.feedback_events[0]
    assert event.feedback_key == "lab1_benign_email_not_progressing"
    assert event.reason_code == REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS
    assert event.trigger_event_index == 12


def test_evaluate_trace_window_once_lab1_malicious_email_emits_not_read_yet_feedback() -> (
    None
):
    task = _make_task()
    malicious_event = EvaluatorTraceEvent(
        event_id=uuid4(),
        session_id=task.session_id,
        family="learner",
        event_type="ATTACK_EMAIL_SENT",
        occurred_at=datetime.now(timezone.utc),
        source="test",
        event_index=12,
        payload={
            "email_id": "email-malicious-1",
            "email_from": "security@vendor.example",
            "subject": "URGENT: update handling rules",
            "malicious_marker": True,
        },
        trace_version=1,
        correlation_id=None,
        request_id=None,
        actor_user_id=None,
        lab_id=task.lab_id,
        lab_version_id=task.lab_version_id,
        lab_difficulty=None,
    )
    repo = _FakeRepo(events=[malicious_event])
    outbox_repo = _FakeOutboxRepo(pending=[])

    service.evaluate_trace_window_once(
        task=task,
        repo=repo,
        lab_lookup_repo=_StubLab1LookupRepo(),
        outbox_repo=outbox_repo,
        classifier=_FakeClassifier(),
    )

    assert outbox_repo.feedback_events_enqueued == 1
    assert len(outbox_repo.feedback_events) == 1
    event = outbox_repo.feedback_events[0]
    assert event.feedback_key == "lab1_malicious_email_not_read_yet"
    assert event.reason_code == REASON_CODE_PI_MALICIOUS_EMAIL_NOT_READ_YET
    assert event.trigger_event_index == 12


def test_evaluate_trace_window_once_maps_poisoned_memory_retrieved_to_objective_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _make_task()
    repo = _FakeRepo(events=[_make_trace_event(task, event_index=0)])
    outbox_repo = _FakeOutboxRepo(pending=[])
    finding = EvaluatorFinding(
        result_type="constraint_violation",
        code="imp.poisoned_memory_retrieved_for_invoice",
        trigger_event_index=6,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="flag",
        reason_code="IMP_POISONED_MEMORY_RETRIEVED_FOR_INVOICE",
        feedback_payload={},
    )

    class _FakeBundle:
        def run(
            self,
            events: list[EvaluatorTraceEvent],
            explanation_signals: tuple[ExplanationSignal, ...],
        ) -> tuple[EvaluatorFinding, ...]:
            _ = (events, explanation_signals)
            return (finding,)

    monkeypatch.setattr(
        service, "resolve_bundle", lambda *, binding, task: _FakeBundle()
    )

    service.evaluate_trace_window_once(
        task=task,
        repo=repo,
        lab_lookup_repo=_StubLabLookupRepo(),
        outbox_repo=outbox_repo,
        classifier=_FakeClassifier(),
    )

    assert outbox_repo.objective_events_enqueued == 1
    event = outbox_repo.objective_events[0]
    assert event.objective_key == "poisoned_memory_retrieved_for_invoice"
    assert event.reason_code == "IMP_POISONED_MEMORY_RETRIEVED_FOR_INVOICE"
    assert event.trigger_event_index == 6
    assert event.idempotency_key == build_objective_event_idempotency_key(
        session_id=task.session_id,
        objective_key="poisoned_memory_retrieved_for_invoice",
        trigger_event_index=6,
    )


def test_evaluate_trace_window_once_maps_payment_routed_to_attacker_to_objective_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _make_task()
    repo = _FakeRepo(events=[_make_trace_event(task, event_index=0)])
    outbox_repo = _FakeOutboxRepo(pending=[])
    finding = EvaluatorFinding(
        result_type="terminal_outcome",
        code="imp.payment_routed_to_attacker_account",
        trigger_event_index=7,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="flag",
        reason_code="IMP_PAYMENT_ROUTED_TO_ATTACKER_ACCOUNT",
        feedback_payload={},
    )

    class _FakeBundle:
        def run(
            self,
            events: list[EvaluatorTraceEvent],
            explanation_signals: tuple[ExplanationSignal, ...],
        ) -> tuple[EvaluatorFinding, ...]:
            _ = (events, explanation_signals)
            return (finding,)

    monkeypatch.setattr(
        service, "resolve_bundle", lambda *, binding, task: _FakeBundle()
    )

    service.evaluate_trace_window_once(
        task=task,
        repo=repo,
        lab_lookup_repo=_StubLabLookupRepo(),
        outbox_repo=outbox_repo,
        classifier=_FakeClassifier(),
    )

    assert outbox_repo.objective_events_enqueued == 1
    event = outbox_repo.objective_events[0]
    assert event.objective_key == "payment_routed_to_attacker_account"
    assert event.reason_code == "IMP_PAYMENT_ROUTED_TO_ATTACKER_ACCOUNT"
    assert event.trigger_event_index == 7
    assert event.idempotency_key == build_objective_event_idempotency_key(
        session_id=task.session_id,
        objective_key="payment_routed_to_attacker_account",
        trigger_event_index=7,
    )


def test_evaluate_trace_window_once_dedupes_objective_enqueue_by_idempotency_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _make_task()
    repo = _FakeRepo(events=[_make_trace_event(task, event_index=0)])
    outbox_repo = _IdempotentObjectiveOutboxRepo(pending=[])
    finding = EvaluatorFinding(
        result_type="constraint_violation",
        code="imp.malicious_vendor_memory_written",
        trigger_event_index=5,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="flag",
        reason_code="IMP_MALICIOUS_VENDOR_MEMORY_WRITTEN",
        feedback_payload={},
    )

    class _FakeBundle:
        def run(
            self,
            events: list[EvaluatorTraceEvent],
            explanation_signals: tuple[ExplanationSignal, ...],
        ) -> tuple[EvaluatorFinding, ...]:
            _ = (events, explanation_signals)
            return (finding,)

    monkeypatch.setattr(
        service, "resolve_bundle", lambda *, binding, task: _FakeBundle()
    )

    service.evaluate_trace_window_once(
        task=task,
        repo=repo,
        lab_lookup_repo=_StubLabLookupRepo(),
        outbox_repo=outbox_repo,
        classifier=_FakeClassifier(),
    )
    service.evaluate_trace_window_once(
        task=task,
        repo=repo,
        lab_lookup_repo=_StubLabLookupRepo(),
        outbox_repo=outbox_repo,
        classifier=_FakeClassifier(),
    )

    assert outbox_repo.objective_events_enqueued == 1
    assert len(outbox_repo.objective_events) == 1
    assert outbox_repo.objective_events[0].objective_key == (
        "malicious_vendor_memory_written"
    )
    assert outbox_repo.objective_events[0].idempotency_key == (
        build_objective_event_idempotency_key(
            session_id=task.session_id,
            objective_key="malicious_vendor_memory_written",
            trigger_event_index=5,
        )
    )


def test_evaluate_trace_window_once_dedupes_feedback_enqueue_by_idempotency_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _make_task()
    repo = _FakeRepo(events=[_make_trace_event(task, event_index=0)])
    outbox_repo = _IdempotentObjectiveOutboxRepo(pending=[])
    finding = EvaluatorFinding(
        result_type="no_effect",
        code="pi.benign_email_injected_no_progress",
        trigger_event_index=11,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code=REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS,
        feedback_payload={},
    )

    class _FakeBundle:
        def run(
            self,
            events: list[EvaluatorTraceEvent],
            explanation_signals: tuple[ExplanationSignal, ...],
        ) -> tuple[EvaluatorFinding, ...]:
            _ = (events, explanation_signals)
            return (finding,)

    monkeypatch.setattr(
        service, "resolve_bundle", lambda *, binding, task: _FakeBundle()
    )

    service.evaluate_trace_window_once(
        task=task,
        repo=repo,
        lab_lookup_repo=_StubLabLookupRepo(),
        outbox_repo=outbox_repo,
        classifier=_FakeClassifier(),
    )
    service.evaluate_trace_window_once(
        task=task,
        repo=repo,
        lab_lookup_repo=_StubLabLookupRepo(),
        outbox_repo=outbox_repo,
        classifier=_FakeClassifier(),
    )

    assert outbox_repo.feedback_events_enqueued == 1
    assert len(outbox_repo.feedback_events) == 1
    event = outbox_repo.feedback_events[0]
    assert event.feedback_key == "lab1_benign_email_not_progressing"
    assert event.reason_code == REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS
    assert event.idempotency_key == build_feedback_event_idempotency_key(
        session_id=task.session_id,
        feedback_key=event.feedback_key,
        reason_code=event.reason_code,
        trigger_event_index=11,
    )


def test_evaluate_trace_window_once_does_not_enqueue_feedback_for_unmapped_finding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _make_task()
    repo = _FakeRepo(events=[_make_trace_event(task, event_index=0)])
    outbox_repo = _FakeOutboxRepo(pending=[])
    finding = EvaluatorFinding(
        result_type="partial_success",
        code="pi.some_other_rule",
        trigger_event_index=3,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code="PI_SOME_OTHER_REASON",
        feedback_payload={},
    )

    class _FakeBundle:
        def run(
            self,
            events: list[EvaluatorTraceEvent],
            explanation_signals: tuple[ExplanationSignal, ...],
        ) -> tuple[EvaluatorFinding, ...]:
            _ = (events, explanation_signals)
            return (finding,)

    monkeypatch.setattr(
        service, "resolve_bundle", lambda *, binding, task: _FakeBundle()
    )

    service.evaluate_trace_window_once(
        task=task,
        repo=repo,
        lab_lookup_repo=_StubLabLookupRepo(),
        outbox_repo=outbox_repo,
        classifier=_FakeClassifier(),
    )

    assert outbox_repo.feedback_events_enqueued == 0
    assert outbox_repo.feedback_events == []


def test_build_session_feedback_created_event_idempotency_key_is_deterministic() -> (
    None
):
    task = _make_task()
    finding = EvaluatorFinding(
        result_type="no_effect",
        code="pi.benign_email_injected_no_progress",
        trigger_event_index=11,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code=REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS,
        feedback_payload={},
    )

    first = service._build_session_feedback_created_event(
        task=task,
        finding=finding,
        created_at=datetime(2026, 4, 23, 12, 0, tzinfo=timezone.utc),
    )
    second = service._build_session_feedback_created_event(
        task=task,
        finding=finding,
        created_at=datetime(2026, 4, 23, 12, 1, tzinfo=timezone.utc),
    )

    assert first is not None
    assert second is not None
    assert first.idempotency_key == second.idempotency_key
