import json
from datetime import datetime, timezone
from uuid import uuid4

import httpx
from openai import OpenAI

from apps.evaluator.src.application.types import LearnerExplanation
from apps.evaluator.src.infrastructure.explanation_classifier import (
    ExplanationClassifierRepository,
)


def _client(handler: httpx.MockTransport) -> OpenAI:
    return OpenAI(
        api_key="test-key",
        base_url="https://openrouter.example/api/v1",
        max_retries=0,
        http_client=httpx.Client(transport=handler),
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


def test_classifier_uses_json_schema_and_returns_validated_signal() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        response_format = body["response_format"]
        assert response_format["type"] == "json_schema"
        assert response_format["json_schema"]["strict"] is True
        assert request.url.path == "/api/v1/chat/completions"
        return httpx.Response(
            200,
            json={
                "id": "completion-1",
                "object": "chat.completion",
                "created": 1,
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": (
                                '{"confidence":0.95,"mentions_trust_boundary":true,'
                                '"mentions_rule_conflict":false,'
                                '"mentions_mitigation":true,'
                                '"mentions_root_cause":true,'
                                '"identified_agent_trusts_external_content":true,'
                                '"identified_rule_priority_clash":false}'
                            ),
                        },
                    }
                ],
            },
        )

    classifier = ExplanationClassifierRepository(
        base_url="https://openrouter.example/api/v1/chat/completions",
        api_key="test-key",
        model="test-model",
        timeout_seconds=5.0,
        client=_client(httpx.MockTransport(_handler)),
    )

    signal = classifier.classify(
        explanations=(_explanation(),),
        lab_difficulty="medium",
    )[0]

    assert signal.confidence == 0.95
    assert signal.mentions_root_cause is True
    assert signal.mentions_mitigation is True
    assert signal.mentions_trust_boundary is True


def test_classifier_http_failure_returns_fallback_signal_without_raising() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection failed", request=request)

    classifier = ExplanationClassifierRepository(
        base_url="https://openrouter.example/api/v1/chat/completions",
        api_key="test-key",
        model="test-model",
        timeout_seconds=5.0,
        client=_client(httpx.MockTransport(_handler)),
    )

    explanation = _explanation()
    signals = classifier.classify(explanations=(explanation,), lab_difficulty="medium")

    assert len(signals) == 1
    assert signals[0].explanation_id == explanation.explanation_id
    assert signals[0].confidence == 0.0
    assert signals[0].mentions_root_cause is False
    assert signals[0].mentions_mitigation is False
    assert signals[0].mentions_rule_conflict is False
    assert signals[0].mentions_trust_boundary is False
