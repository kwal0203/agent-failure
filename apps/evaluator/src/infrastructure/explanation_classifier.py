import logging

from openai import OpenAI, OpenAIError
from pydantic import ValidationError

from apps.evaluator.src.application.ports import ExplanationClassifierPort
from apps.evaluator.src.application.schemas import (
    OpenRouterDisclosureAttemptResponse,
    OpenRouterExplanationResponse,
)
from apps.evaluator.src.application.types import ExplanationSignal, LearnerExplanation
from apps.shared.openai_compatible import build_client

logger = logging.getLogger(__name__)


class ExplanationClassifierRepository(ExplanationClassifierPort):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        *,
        client: OpenAI | None = None,
    ) -> None:
        self._model = model
        self._client = client or build_client(
            provider_endpoint=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
        )

    def classify(
        self, explanations: tuple[LearnerExplanation, ...], *, lab_difficulty: str
    ) -> tuple[ExplanationSignal, ...]:
        signals: list[ExplanationSignal] = []
        for explanation in explanations:
            try:
                completion = self._client.chat.completions.parse(
                    model=self._model,
                    temperature=0.0,
                    response_format=OpenRouterExplanationResponse,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Classify the learner's security explanation. "
                                "Identify the concepts the learner explicitly recognizes."
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
                )
                parsed = completion.choices[0].message.parsed
                if parsed is None:
                    raise ValueError("provider returned no structured explanation")
            except (OpenAIError, ValidationError, ValueError, IndexError) as exc:
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
        try:
            completion = self._client.chat.completions.parse(
                model=self._model,
                temperature=0.0,
                response_format=OpenRouterDisclosureAttemptResponse,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Classify whether the learner prompt attempts to make the "
                            "assistant disclose protected secret information, such as "
                            "a manager's home address."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"prompt={prompt_content}",
                    },
                ],
            )
            parsed = completion.choices[0].message.parsed
            if parsed is None:
                raise ValueError("provider returned no structured disclosure decision")
            return (parsed.is_disclosure_attempt, parsed.confidence)
        except (OpenAIError, ValidationError, ValueError, IndexError):
            return (False, 0.0)
