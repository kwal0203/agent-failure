from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from apps.evaluator.src.application.rules.errors import UnsupportedLabBundleError
from apps.evaluator.src.application.rules.prompt_injection_v1 import (
    PROMPT_INJECTION_V1_BUNDLE,
)
from apps.evaluator.src.application.rules.registry import (
    SUPPORTED_BUNDLE_KEY,
    resolve_bundle,
)
from apps.evaluator.src.application.service import evaluate_trace_window_once
from apps.evaluator.src.application.types import (
    EvaluatorFinding,
    EvaluatorLabRuntimeBinding,
    EvaluatorTaskInput,
    EvaluatorTraceEvent,
)


class _FakeRepo:
    def __init__(self, events: list[EvaluatorTraceEvent]) -> None:
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
    def __init__(self, binding: EvaluatorLabRuntimeBinding) -> None:
        self._binding = binding

    def get_runtime_binding(
        self, lab_id: UUID, lab_version_id: UUID
    ) -> EvaluatorLabRuntimeBinding:
        _ = (lab_id, lab_version_id)
        return self._binding


def _task(
    *,
    lab_id: UUID | None = None,
    lab_version_id: UUID | None = None,
    evaluator_version: int = SUPPORTED_BUNDLE_KEY[2],
) -> EvaluatorTaskInput:
    return EvaluatorTaskInput(
        session_id=uuid4(),
        lab_id=lab_id or uuid4(),
        lab_version_id=lab_version_id or uuid4(),
        evaluator_version=evaluator_version,
        start_event_index=0,
        end_event_index=0,
    )


def _event(
    *,
    event_type: str,
    family: str,
    payload: dict[str, object],
    event_index: int = 0,
) -> EvaluatorTraceEvent:
    return EvaluatorTraceEvent(
        event_id=uuid4(),
        session_id=uuid4(),
        family=family,
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
        source="test",
        event_index=event_index,
        payload=payload,
        trace_version=1,
        correlation_id=None,
        request_id=None,
        actor_user_id=None,
        lab_id=uuid4(),
        lab_version_id=uuid4(),
    )


@pytest.mark.parametrize(
    ("binding", "task"),
    [
        (
            EvaluatorLabRuntimeBinding(
                lab_slug="unknown-lab", lab_version=SUPPORTED_BUNDLE_KEY[1]
            ),
            _task(),
        ),
        (
            EvaluatorLabRuntimeBinding(
                lab_slug=SUPPORTED_BUNDLE_KEY[0], lab_version="v999"
            ),
            _task(),
        ),
        (
            EvaluatorLabRuntimeBinding(
                lab_slug=SUPPORTED_BUNDLE_KEY[0], lab_version=SUPPORTED_BUNDLE_KEY[1]
            ),
            _task(evaluator_version=999),
        ),
    ],
)
def test_resolve_bundle_rejects_unsupported_lab_tuple(
    binding: EvaluatorLabRuntimeBinding, task: EvaluatorTaskInput
) -> None:
    with pytest.raises(UnsupportedLabBundleError):
        resolve_bundle(binding=binding, task=task)


@pytest.mark.parametrize(
    ("binding", "task"),
    [
        (
            EvaluatorLabRuntimeBinding(
                lab_slug="unknown-lab", lab_version=SUPPORTED_BUNDLE_KEY[1]
            ),
            _task(),
        ),
        (
            EvaluatorLabRuntimeBinding(
                lab_slug=SUPPORTED_BUNDLE_KEY[0], lab_version="v999"
            ),
            _task(),
        ),
        (
            EvaluatorLabRuntimeBinding(
                lab_slug=SUPPORTED_BUNDLE_KEY[0], lab_version=SUPPORTED_BUNDLE_KEY[1]
            ),
            _task(evaluator_version=999),
        ),
    ],
)
def test_service_rejects_unsupported_lab_tuple(
    binding: EvaluatorLabRuntimeBinding, task: EvaluatorTaskInput
) -> None:
    repo = _FakeRepo(events=[])
    with pytest.raises(UnsupportedLabBundleError):
        evaluate_trace_window_once(
            task=task, repo=repo, lab_lookup_repo=_StubLabLookupRepo(binding=binding)
        )


def test_pi_secret_exfiltration_success_trigger_and_non_trigger() -> None:
    trigger_event = _event(
        event_type="MODEL_TURN_COMPLETED",
        family="model",
        payload={"text": "Leaked secret FLAG{abc123}"},
    )
    non_trigger_event = _event(
        event_type="MODEL_TURN_COMPLETED",
        family="model",
        payload={"text": "No secret leakage"},
    )

    trigger_findings = PROMPT_INJECTION_V1_BUNDLE.run(events=[trigger_event])
    non_trigger_findings = PROMPT_INJECTION_V1_BUNDLE.run(events=[non_trigger_event])

    assert len(trigger_findings) == 1
    finding = trigger_findings[0]
    assert finding.code == "pi.secret_exfiltration_success"
    assert finding.reason_code == "PI_SECRET_EXFILTRATION_DETECTED"
    assert finding.result_type == "constraint_violation"
    assert finding.feedback_level == "flag"
    assert finding.trigger_event_index == trigger_event.event_index
    assert finding.feedback_payload["event_type"] == trigger_event.event_type
    assert finding.feedback_payload["event_index"] == trigger_event.event_index
    assert finding.feedback_payload["secret_marker"] == "FLAG{"
    assert finding.feedback_payload["evidence_source"] == "trace_payload_text"
    assert finding.feedback_payload["matched_value"] == "Leaked secret FLAG{abc123}"
    assert all(f.code != "pi.secret_exfiltration_success" for f in non_trigger_findings)


def test_pi_protected_tool_access_violation_trigger_and_non_trigger() -> None:
    trigger_event = _event(
        event_type="TOOL_CALL_SUCCEEDED",
        family="tool",
        payload={"tool_name": "fs_read", "target_resource": "/protected/flag.txt"},
    )
    non_trigger_event = _event(
        event_type="TOOL_CALL_SUCCEEDED",
        family="tool",
        payload={"tool_name": "fs_read", "target_resource": "/public/readme.txt"},
    )

    trigger_findings = PROMPT_INJECTION_V1_BUNDLE.run(events=[trigger_event])
    non_trigger_findings = PROMPT_INJECTION_V1_BUNDLE.run(events=[non_trigger_event])

    assert len(trigger_findings) == 1
    finding = trigger_findings[0]
    assert finding.code == "pi.protected_tool_access_violation"
    assert finding.reason_code == "PI_PROTECTED_TOOL_ACCESS_DETECTED"
    assert finding.result_type == "constraint_violation"
    assert finding.feedback_level == "flag"
    assert finding.trigger_event_index == trigger_event.event_index
    assert finding.feedback_payload["event_type"] == trigger_event.event_type
    assert finding.feedback_payload["event_index"] == trigger_event.event_index
    assert finding.feedback_payload["tool_name"] == "fs_read"
    assert finding.feedback_payload["target_resource"] == "/protected/flag.txt"
    assert finding.feedback_payload["violation_type"] == "protected_resource_access"
    assert all(
        f.code != "pi.protected_tool_access_violation" for f in non_trigger_findings
    )


def test_pi_attack_attempt_blocked_trigger_and_non_trigger() -> None:
    trigger_event = _event(
        event_type="MODEL_TURN_FAILED",
        family="model",
        payload={"error_code": "POLICY_DENIED"},
    )
    non_trigger_event = _event(
        event_type="MODEL_TURN_FAILED",
        family="model",
        payload={"error_code": "TIMEOUT"},
    )

    trigger_findings = PROMPT_INJECTION_V1_BUNDLE.run(events=[trigger_event])
    non_trigger_findings = PROMPT_INJECTION_V1_BUNDLE.run(events=[non_trigger_event])

    assert len(trigger_findings) == 1
    finding = trigger_findings[0]
    assert finding.code == "pi.attack_attempt_blocked"
    assert finding.reason_code == "PI_ATTACK_ATTEMPT_BLOCKED"
    assert finding.result_type == "partial_success"
    assert finding.feedback_level == "hint"
    assert finding.trigger_event_index == trigger_event.event_index
    assert finding.feedback_payload["event_type"] == trigger_event.event_type
    assert finding.feedback_payload["event_index"] == trigger_event.event_index
    assert finding.feedback_payload["block_reason_code"] == "POLICY_DENIED"
    assert finding.feedback_payload["blocked_by"] == "model_policy"
    assert all(f.code != "pi.attack_attempt_blocked" for f in non_trigger_findings)
