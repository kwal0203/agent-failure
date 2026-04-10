from datetime import datetime, timezone
from uuid import uuid4

import httpx

from apps.evaluator.src.application.types import LearnerExplanation
from apps.evaluator.src.infrastructure.explanation_classifier import (
    ExplanationClassifierRepository,
)


class _RaisingClient:
    def post(self, url: str, json: dict[str, object]) -> object:
        _ = (url, json)
        raise httpx.ConnectError(
            "connection failed",
            request=httpx.Request(
                "POST", "https://openrouter.example/chat/completions"
            ),
        )


def _explanation() -> LearnerExplanation:
    now = datetime.now(timezone.utc)
    return LearnerExplanation(
        explanation_id=uuid4(),
        explanation="The model followed untrusted email instructions.",
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        lab_difficulty="medium",
        source="learner",
        actor_user_id=uuid4(),
        idempotency_key="idempo-test",
        created_at=now,
    )


def test_classifier_http_failure_returns_fallback_signal_without_raising() -> None:
    classifier = ExplanationClassifierRepository(
        base_url="https://openrouter.example/chat/completions",
        api_key="test-key",
        model="test-model",
        timeout_seconds=5.0,
    )
    classifier._client = _RaisingClient()  # type: ignore[assignment]

    explanation = _explanation()
    signals = classifier.classify(explanations=(explanation,), lab_difficulty="medium")

    assert len(signals) == 1
    assert signals[0].explanation_id == explanation.explanation_id
    assert signals[0].confidence == 0.0
    assert signals[0].mentions_root_cause is False
    assert signals[0].mentions_mitigation is False
    assert signals[0].mentions_rule_conflict is False
    assert signals[0].mentions_trust_boundary is False
