import json
from collections.abc import Callable

import httpx
import pytest

from apps.agent_harness.src.application.session_loop.errors import (
    SessionLoopProviderFailureError,
)
from apps.agent_harness.src.application.session_loop.types import (
    ChatMessage,
    ModelRequest,
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


def _make_mock_client_factory(
    handler: Callable[[httpx.Request], httpx.Response],
) -> Callable[..., httpx.Client]:
    transport = httpx.MockTransport(handler)
    real_client = httpx.Client

    def _factory(*args: object, **kwargs: object) -> httpx.Client:
        _ = args, kwargs
        return real_client(transport=transport)

    return _factory


def test_gateway_client_streams_chunks_successfully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        assert body["model"] == "openai/gpt-5.2"
        assert body["stream"] is True
        assert body["messages"][1]["content"] == "Explain prompt injection basics"
        assert request.headers["authorization"].startswith("Bearer ")

        sse = (
            'data: {"choices":[{"delta":{"content":"Hello "}}]}\n\n'
            'data: {"choices":[{"delta":{"content":"world"}}]}\n\n'
            "data: [DONE]\n\n"
        )
        return httpx.Response(
            status_code=200,
            headers={"Content-Type": "text/event-stream"},
            content=sse.encode("utf-8"),
        )

    import apps.agent_harness.src.infrastructure.model.gateway_client as gateway_module

    monkeypatch.setattr(
        gateway_module.httpx,
        "Client",
        _make_mock_client_factory(_handler),
    )

    client = GatewayModelClient(
        config=GatewayConfig(
            endpoint="https://openrouter.ai/api/v1/chat/completions",
            api_key="test-key",
            model="openai/gpt-5.2",
            timeout_seconds=5.0,
        )
    )

    chunks = list(client.stream(_build_request()))
    assert [chunk.content for chunk in chunks] == ["Hello ", "world", ""]
    assert [chunk.final for chunk in chunks] == [False, False, True]


def test_gateway_client_auth_failure_raises_typed_provider_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return httpx.Response(status_code=401, content=b'{"error":"unauthorized"}')

    import apps.agent_harness.src.infrastructure.model.gateway_client as gateway_module

    monkeypatch.setattr(
        gateway_module.httpx,
        "Client",
        _make_mock_client_factory(_handler),
    )

    client = GatewayModelClient(
        config=GatewayConfig(
            endpoint="https://openrouter.ai/api/v1/chat/completions",
            api_key="bad-key",
            model="openai/gpt-5.2",
            timeout_seconds=5.0,
        )
    )

    with pytest.raises(SessionLoopProviderFailureError) as exc_info:
        list(client.stream(_build_request()))

    assert exc_info.value.message == "Provider authentication failed"
    assert exc_info.value.details.get("status_code") == "401"
