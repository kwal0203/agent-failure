from uuid import UUID
from collections.abc import Sequence

from apps.evaluator.src.application.types import EvaluatorFinding, EvaluatorTraceEvent
from apps.evaluator.src.application.rules.types import RuleBundle, RuleFn
from apps.evaluator.src.application.rules.common import TEXT_PAYLOAD_FIELDS
from apps.evaluator.src.application.rules.contract import RULE_ID_RAG_POISON_DETECTED


POISONING_MARKERS = (
    "ignore previous instructions",
    "disregard prior instructions",
    "system prompt",
    "developer message",
)


def _extract_text_candidates(payload: dict[str, object]) -> list[str]:
    values: list[str] = []
    for key in TEXT_PAYLOAD_FIELDS:
        value = payload.get(key)
        if isinstance(value, str):
            values.append(value)
    return values


def _contains_poisoning_marker(texts: Sequence[str]) -> str | None:
    lowered = [text.lower() for text in texts]
    for marker in POISONING_MARKERS:
        if any(marker in text for text in lowered):
            return marker
    return None


def _rule_rag_poisoning_signal_detected(
    event: EvaluatorTraceEvent,
) -> EvaluatorFinding | None:
    if event.event_type not in {"MODEL_TURN_COMPLETED", "TOOL_CALL_SUCCEEDED"}:
        return None

    payload = event.payload or {}
    text_candidates = _extract_text_candidates(payload)
    marker = _contains_poisoning_marker(text_candidates)
    if marker is None:
        return None

    return EvaluatorFinding(
        result_type="partial_success",
        code=RULE_ID_RAG_POISON_DETECTED,
        trigger_event_index=event.event_index,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="hint",
        reason_code="RAG_POISONING_SIGNAL_DETECTED",
        feedback_payload={
            "event_type": event.event_type,
            "event_index": event.event_index,
            "marker": marker,
            "evidence_source": "trace_payload_text",
        },
    )


RULES: tuple[RuleFn, ...] = (_rule_rag_poisoning_signal_detected,)

RAG_POISONING_V1_BUNDLE = RuleBundle(
    name="rag_poisoning_v1",
    lab_id=UUID("22222222-2222-2222-2222-222222222222"),
    lab_version_id=UUID("66666666-6666-6666-6666-666666666666"),
    evaluator_version=1,
    rules=RULES,
)
