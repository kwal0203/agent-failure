from apps.evaluator.src.application.types import EvaluatorTraceEvent

import re


def _normalize_text(value: str) -> str:
    lowered = value.lower()
    collapsed = re.sub(r"\s+", " ", lowered)
    return collapsed.strip()


def extract_learner_text(event: EvaluatorTraceEvent) -> str | None:
    payload = event.payload or {}
    for key in ("content", "email_body", "body", "message", "text"):
        raw = payload.get(key)
        if isinstance(raw, str) and raw.strip():
            return _normalize_text(raw)

    return None


def matched_pattern_strings(
    text: str, patterns: tuple[re.Pattern[str], ...]
) -> list[str]:
    matched: list[str] = []
    for pat in patterns:
        if pat.search(text):
            matched.append(pat.pattern)
    return matched
