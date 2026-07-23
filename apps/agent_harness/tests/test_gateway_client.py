import json
from collections.abc import Callable

import httpx
import pytest
from openai import OpenAI

from apps.agent_harness.src.application.session_loop.errors import (
    SessionLoopProviderFailureError,
)
from apps.agent_harness.src.application.session_loop.types import (
    AgentRequest,
    AgentToolCallResponse,
    ChatMessage,
    ModelRequest,
    ToolDefinition,
)
from apps.agent_harness.src.infrastructure.model.gateway_client import (
    GatewayModelClient,
)
from apps.agent_harness.src.infrastructure.model.types import GatewayConfig


def _build_request() -> ModelRequest:
    return ModelRequest(
        messages=[
            ChatMessage(role="system", content="You are a lab assistant"),
            ChatMessage(role="user", content="Explain prompt injection basics"),
        ]
    )


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> OpenAI:
    return OpenAI(
        api_key="test-key",
        base_url="https://openrouter.ai/api/v1",
        max_retries=0,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def _gateway(handler: Callable[[httpx.Request], httpx.Response]) -> GatewayModelClient:
    return GatewayModelClient(
        config=GatewayConfig(
            endpoint="https://openrouter.ai/api/v1/chat/completions",
            api_key="test-key",
            model="openai/gpt-5.2",
            timeout_seconds=5.0,
        ),
        client=_client(handler),
    )


def _completion(content: str) -> dict[str, object]:
    return {
        "id": "completion-1",
        "object": "chat.completion",
        "created": 1,
        "model": "openai/gpt-5.2",
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": content},
            }
        ],
    }


def test_gateway_client_streams_chunks_successfully() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "openai/gpt-5.2"
        assert body["stream"] is True
        assert body["messages"][1]["content"] == "Explain prompt injection basics"
        assert request.headers["authorization"].startswith("Bearer ")
        assert request.url.path == "/api/v1/chat/completions"

        sse = (
            'data: {"id":"1","object":"chat.completion.chunk","created":1,'
            '"model":"test","choices":[{"index":0,"delta":{"content":"Hello "},'
            '"finish_reason":null}]}\n\n'
            'data: {"id":"1","object":"chat.completion.chunk","created":1,'
            '"model":"test","choices":[{"index":0,"delta":{"content":"world"},'
            '"finish_reason":null}]}\n\n'
            "data: [DONE]\n\n"
        )
        return httpx.Response(
            status_code=200,
            headers={"Content-Type": "text/event-stream"},
            content=sse.encode(),
        )

    chunks = list(_gateway(_handler).stream(_build_request()))

    assert [chunk.content for chunk in chunks] == ["Hello ", "world", ""]
    assert [chunk.final for chunk in chunks] == [False, False, True]


def test_gateway_client_complete_uses_non_streaming_request() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is False
        return httpx.Response(200, json=_completion("Complete response"))

    assert _gateway(_handler).complete(_build_request()) == "Complete response"


def test_gateway_client_decision_uses_strict_json_schema() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["response_format"]["type"] == "json_schema"
        assert body["response_format"]["json_schema"]["strict"] is True
        return httpx.Response(
            200,
            json=_completion(
                '{"kind":"tool_call","tool_name":"read_email",'
                '"args":{"email_id":"email-1"}}'
            ),
        )

    decision = _gateway(_handler).decide_tool_or_text(_build_request())

    assert decision.kind == "tool_call"
    assert decision.tool_name == "read_email"
    assert decision.args == {"email_id": "email-1"}


def test_gateway_client_uses_sdk_tool_call_response() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["tool_choice"] == "auto"
        assert body["tools"][0]["function"]["name"] == "read_email"
        return httpx.Response(
            200,
            json={
                "id": "completion-1",
                "object": "chat.completion",
                "created": 1,
                "model": "openai/gpt-5.2",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "tool_calls",
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "type": "function",
                                    "function": {
                                        "name": "read_email",
                                        "arguments": '{"email_id":"email-1"}',
                                    },
                                }
                            ],
                        },
                    }
                ],
            },
        )

    result = _gateway(_handler).agent_chat(
        AgentRequest(
            messages=_build_request().messages,
            tools=[
                ToolDefinition(
                    name="read_email",
                    description="Read an email",
                    parameters={
                        "type": "object",
                        "properties": {"email_id": {"type": "string"}},
                        "required": ["email_id"],
                    },
                )
            ],
        )
    )

    assert isinstance(result, AgentToolCallResponse)
    assert result.tool_calls[0].tool_name == "read_email"
    assert result.tool_calls[0].args == {"email_id": "email-1"}


def test_gateway_client_auth_failure_raises_typed_provider_failure() -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(
            status_code=401,
            json={"error": {"message": "unauthorized", "type": "auth_error"}},
        )

    with pytest.raises(SessionLoopProviderFailureError) as exc_info:
        list(_gateway(_handler).stream(_build_request()))

    assert exc_info.value.message == "Provider authentication failed"
    assert exc_info.value.details.get("status_code") == "401"
