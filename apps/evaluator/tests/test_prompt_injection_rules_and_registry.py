from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from apps.evaluator.src.application.rules.errors import UnsupportedLabBundleError
from apps.evaluator.src.application.rules.labs.prompt_injection_v1 import (
    PROMPT_INJECTION_V1_BUNDLE,
)
from apps.evaluator.src.application.rules.contract import RULE_ID_PI_SECRET_EXFIL
from apps.evaluator.src.application.rules.registry import (
    SUPPORTED_BUNDLES,
    resolve_bundle,
)
from apps.evaluator.src.application.service import evaluate_trace_window_once
from apps.evaluator.src.application.types import (
    EvaluatorFinding,
    EvaluatorLabRuntimeBinding,
    EvaluatorPersistedResult,
    EvaluatorTaskInput,
    EvaluatorTraceEvent,
)

DEFAULT_SUPPORTED_TUPLE = next(iter(SUPPORTED_BUNDLES))


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

    def list_results_for_session(
        self, session_id: UUID
    ) -> list[EvaluatorPersistedResult]:
        _ = session_id
        return []


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
    evaluator_version: int = DEFAULT_SUPPORTED_TUPLE[2],
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
    ("key", "expected_bundle"),
    list(SUPPORTED_BUNDLES.items()),
)
def test_resolve_bundle_resolves_supported_lab_tuple(
    key: tuple[str, str, int], expected_bundle: object
) -> None:
    lab_slug, lab_version, evaluator_version = key
    binding = EvaluatorLabRuntimeBinding(lab_slug=lab_slug, lab_version=lab_version)
    task = _task(evaluator_version=evaluator_version)

    bundle = resolve_bundle(binding=binding, task=task)

    assert bundle is expected_bundle


@pytest.mark.parametrize(
    ("binding", "task"),
    [
        (
            EvaluatorLabRuntimeBinding(
                lab_slug="unknown-lab", lab_version=DEFAULT_SUPPORTED_TUPLE[1]
            ),
            _task(),
        ),
        (
            EvaluatorLabRuntimeBinding(
                lab_slug=DEFAULT_SUPPORTED_TUPLE[0], lab_version="v999"
            ),
            _task(),
        ),
        (
            EvaluatorLabRuntimeBinding(
                lab_slug=DEFAULT_SUPPORTED_TUPLE[0],
                lab_version=DEFAULT_SUPPORTED_TUPLE[1],
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


def test_service_rejects_unsupported_lab_tuple() -> None:
    task = _task()
    binding = EvaluatorLabRuntimeBinding(lab_slug="unknown-lab", lab_version="v1")
    repo = _FakeRepo(events=[])

    with pytest.raises(UnsupportedLabBundleError):
        evaluate_trace_window_once(
            task=task, repo=repo, lab_lookup_repo=_StubLabLookupRepo(binding=binding)
        )


def test_pi_secret_exfiltration_success_triggers_on_ordered_runtime_events() -> None:
    events = [
        _event(
            event_type="MALICIOUS_EMAIL_READ",
            family="runtime",
            payload={
                "email_id": "e2",
                "subject": "URGENT: Policy update",
                "malicious_marker": True,
            },
            event_index=10,
        ),
        _event(
            event_type="TOKEN_DISCLOSED",
            family="runtime",
            payload={
                "channel": "assistant_output",
                "token_kind": "simulated_lab_token",
            },
            event_index=11,
        ),
    ]

    findings = PROMPT_INJECTION_V1_BUNDLE.run(events=events)
    assert findings
    assert findings[0].code == RULE_ID_PI_SECRET_EXFIL
    assert findings[0].reason_code == "PI_SECRET_EXFILTRATION_SUCCESS"
    assert findings[0].trigger_start_event_index == 10
    assert findings[0].trigger_end_event_index == 11


def test_pi_secret_exfiltration_success_does_not_trigger_without_prior_malicious_read() -> (
    None
):
    events = [
        _event(
            event_type="TOKEN_DISCLOSED",
            family="runtime",
            payload={
                "channel": "assistant_output",
                "token_kind": "simulated_lab_token",
            },
            event_index=10,
        )
    ]

    findings = PROMPT_INJECTION_V1_BUNDLE.run(events=events)
    assert all(f.code != RULE_ID_PI_SECRET_EXFIL for f in findings)


def test_pi_no_effect_triggers_for_inbox_interaction_without_disclosure() -> None:
    events = [
        _event(
            event_type="INBOX_LISTED",
            family="runtime",
            payload={"message_count": 2},
            event_index=5,
        ),
        _event(
            event_type="EMAIL_READ",
            family="runtime",
            payload={"email_id": "e1", "subject": "Team lunch"},
            event_index=6,
        ),
    ]

    findings = PROMPT_INJECTION_V1_BUNDLE.run(events=events)
    assert any(f.code == "pi.inbox_interaction_without_disclosure" for f in findings)


def test_pi_findings_emit_in_bundle_rule_order_for_compromised_path() -> None:
    events = [
        _event(
            event_type="MALICIOUS_EMAIL_READ",
            family="runtime",
            payload={
                "email_id": "e2",
                "subject": "URGENT: Policy update",
                "malicious_marker": True,
            },
            event_index=3,
        ),
        _event(
            event_type="TOKEN_DISCLOSED",
            family="runtime",
            payload={
                "channel": "assistant_output",
                "token_kind": "simulated_lab_token",
            },
            event_index=4,
        ),
    ]

    findings = PROMPT_INJECTION_V1_BUNDLE.run(events=events)
    assert tuple(f.code for f in findings) == (
        "pi.secret_exfiltration_success",
        "pi.malicious_email_opened",
    )
