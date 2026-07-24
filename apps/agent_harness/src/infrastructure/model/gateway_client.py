import json
from collections.abc import Iterable
from typing import NoReturn, cast

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    OpenAIError,
    PermissionDeniedError,
)
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam
from pydantic import ValidationError

from apps.agent_harness.src.application.session_loop.errors import (
    SessionLoopProviderFailureError,
)
from apps.agent_harness.src.application.session_loop.ports import ModelClientPort
from apps.agent_harness.src.application.session_loop.types import (
    AgentRequest,
    AgentResponse,
    AgentTextResponse,
    AgentToolCallResponse,
    ChatMessage,
    HarnessChunk,
    ModelRequest,
    ToolCallResult,
    ToolDecision,
)
from apps.agent_harness.src.infrastructure.model.schemas import LLMDecisionResponse
from apps.agent_harness.src.infrastructure.model.types import GatewayConfig
from apps.shared.openai_compatible import build_client


def _message_params(messages: list[ChatMessage]) -> list[ChatCompletionMessageParam]:
    serialized: list[dict[str, object]] = []
    for message in messages:
        item: dict[str, object] = {
            "role": message.role,
            "content": message.content,
        }
        if message.tool_call_id is not None:
            item["tool_call_id"] = message.tool_call_id
        if message.tool_calls:
            item["tool_calls"] = [
                {
                    "id": tool_call.call_id,
                    "type": "function",
                    "function": {
                        "name": tool_call.tool_name,
                        "arguments": tool_call.arguments,
                    },
                }
                for tool_call in message.tool_calls
            ]
        serialized.append(item)
    return cast(list[ChatCompletionMessageParam], serialized)


def _tool_params(request: AgentRequest) -> list[ChatCompletionToolParam]:
    serialized = [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": dict(tool.parameters),
            },
        }
        for tool in request.tools
    ]
    return cast(list[ChatCompletionToolParam], serialized)


def _raise_provider_failure(exc: OpenAIError) -> NoReturn:
    details = {"error": str(exc)}
    if isinstance(exc, APIStatusError):
        details["status_code"] = str(exc.status_code)

    if isinstance(exc, APITimeoutError):
        message = "Provider request timed out"
    elif isinstance(exc, (AuthenticationError, PermissionDeniedError)):
        message = "Provider authentication failed"
    elif isinstance(exc, APIConnectionError):
        message = "Provider unavailable"
    else:
        message = "Provider returned invalid response"

    raise SessionLoopProviderFailureError(message=message, details=details) from exc


class GatewayModelClient(ModelClientPort):
    def __init__(self, config: GatewayConfig, *, client: OpenAI | None = None) -> None:
        self._config = config
        self._client = client or build_client(
            provider_endpoint=config.endpoint,
            api_key=config.api_key,
            timeout_seconds=config.timeout_seconds,
        )

    def stream(self, payload: ModelRequest) -> Iterable[HarnessChunk]:
        try:
            stream = self._client.chat.completions.create(
                model=self._config.model,
                messages=_message_params(payload.messages),
                stream=True,
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content if chunk.choices else None
                if content:
                    yield HarnessChunk(content=content, final=False)
        except OpenAIError as exc:
            _raise_provider_failure(exc)
        except Exception as exc:
            raise SessionLoopProviderFailureError(
                message="Model provider request failed",
                details={"error": str(exc)},
            ) from exc

        yield HarnessChunk(content="", final=True)

    def complete(self, payload: ModelRequest) -> str:
        try:
            completion = self._client.chat.completions.create(
                model=self._config.model,
                messages=_message_params(payload.messages),
                stream=False,
            )
            if not completion.choices:
                return ""
            return completion.choices[0].message.content or ""
        except OpenAIError as exc:
            _raise_provider_failure(exc)
        except Exception as exc:
            raise SessionLoopProviderFailureError(
                message="Model provider request failed",
                details={"error": str(exc)},
            ) from exc

    def decide_tool_or_text(self, payload: ModelRequest) -> ToolDecision:
        try:
            completion = self._client.chat.completions.parse(
                model=self._config.model,
                messages=_message_params(payload.messages),
                temperature=0,
                response_format=LLMDecisionResponse,
            )
            parsed = completion.choices[0].message.parsed
            if parsed is None:
                return ToolDecision(kind="text", tool_name=None, args={}, text=None)
            decision = parsed.root
        except OpenAIError as exc:
            _raise_provider_failure(exc)
        except (IndexError, TypeError, ValueError, ValidationError):
            return ToolDecision(kind="text", tool_name=None, args={}, text=None)

        if decision.kind == "tool_call":
            return ToolDecision(
                kind="tool_call",
                tool_name=decision.tool_name,
                args=decision.args,
                text=None,
            )

        return ToolDecision(
            kind="text",
            tool_name=None,
            args={},
            text=decision.text if decision.text and decision.text.strip() else None,
        )

    def agent_chat(self, payload: AgentRequest) -> AgentResponse:
        try:
            completion = self._client.chat.completions.create(
                model=self._config.model,
                messages=_message_params(payload.messages),
                stream=False,
                tools=_tool_params(payload),
                tool_choice="auto",
            )
            message = completion.choices[0].message

            if message.tool_calls:
                return AgentToolCallResponse(
                    tool_calls=[
                        ToolCallResult(
                            call_id=tool_call.id,
                            tool_name=tool_call.function.name,
                            args=json.loads(tool_call.function.arguments),
                        )
                        for tool_call in message.tool_calls
                        if tool_call.type == "function"
                    ]
                )

            return AgentTextResponse(content=message.content or "")
        except OpenAIError as exc:
            _raise_provider_failure(exc)
        except (IndexError, json.JSONDecodeError, TypeError, ValidationError) as exc:
            raise SessionLoopProviderFailureError(
                message="Provider returned invalid agent response",
                details={"error": str(exc)},
            ) from exc
