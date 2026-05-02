from apps.evaluator.src.application.ports import ExplanationClassifierPort
from apps.evaluator.src.application.types import ExplanationSignal, LearnerExplanation
from apps.evaluator.src.application.schemas import (
    OpenRouterDisclosureAttemptResponse,
    OpenRouterExplanationResponse,
)
from pydantic import ValidationError

import httpx
import logging

logger = logging.getLogger(__name__)


class ExplanationClassifierRepository(ExplanationClassifierPort):
    def __init__(
        self, base_url: str, api_key: str, model: str, timeout_seconds: float
    ) -> None:
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=self._timeout_seconds,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

    def classify(
        self, explanations: tuple[LearnerExplanation, ...], *, lab_difficulty: str
    ) -> tuple[ExplanationSignal, ...]:
        signals: list[ExplanationSignal] = []
        for explanation in explanations:
            payload: dict[str, object] = {
                "model": self._model,
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Classify learner security explanation. "
                            "Return strict JSON with booleans: "
                            "mentions_root_cause, mentions_mitigation, "
                            "mentions_rule_conflict, mentions_trust_boundary, "
                            "and numeric confidence 0..1."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"tier={lab_difficulty}\n"
                            f"explanation={explanation.explanation}"
                        ),
                    },
                ],
            }

            try:
                resp = self._client.post("", json=payload)
                resp.raise_for_status()
                body = resp.json()
                content = (
                    body.get("choices", [{}])[0].get("message", {}).get("content", "{}")
                )
                parsed = OpenRouterExplanationResponse.model_validate_json(content)
            except (httpx.HTTPError, ValidationError, ValueError) as exc:
                logger.warning(
                    "explanation classification failed",
                    extra={
                        "event": "explanation_classification_failed",
                        "explanation_id": str(explanation.explanation_id),
                        "session_id": str(explanation.session_id),
                        "lab_id": str(explanation.lab_id),
                        "lab_difficulty": lab_difficulty,
                        "error_type": type(exc).__name__,
                    },
                )
                signals.append(
                    ExplanationSignal(
                        explanation_id=explanation.explanation_id,
                        confidence=0.0,
                    )
                )
                continue

            signals.append(
                ExplanationSignal(
                    explanation_id=explanation.explanation_id,
                    mentions_root_cause=parsed.mentions_root_cause,
                    mentions_mitigation=parsed.mentions_mitigation,
                    mentions_rule_conflict=parsed.mentions_rule_conflict,
                    mentions_trust_boundary=parsed.mentions_trust_boundary,
                    identified_agent_trusts_external_content=parsed.identified_agent_trusts_external_content,
                    identified_rule_priority_clash=parsed.identified_rule_priority_clash,
                    confidence=parsed.confidence,
                )
            )

        return tuple(signals)

    def classify_disclosure_attempt(self, *, prompt_content: str) -> tuple[bool, float]:
        payload: dict[str, object] = {
            "model": self._model,
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Classify whether the learner prompt is an attempt to get the "
                        "assistant to disclose protected secret information (such as a "
                        "manager home address). Return strict JSON with keys: "
                        "is_disclosure_attempt (boolean), confidence (0..1), reason (string|null)."
                    ),
                },
                {"role": "user", "content": f"prompt={prompt_content}"},
            ],
        }

        try:
            resp = self._client.post("", json=payload)
            resp.raise_for_status()
            body = resp.json()
            content = (
                body.get("choices", [{}])[0].get("message", {}).get("content", "{}")
            )
            parsed = OpenRouterDisclosureAttemptResponse.model_validate_json(content)
            return (parsed.is_disclosure_attempt, parsed.confidence)
        except (httpx.HTTPError, ValidationError, ValueError):
            return (False, 0.0)
