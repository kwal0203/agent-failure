from typing import Iterable
from pydantic import ValidationError, TypeAdapter

from apps.agent_harness.src.application.session_loop.ports import ModelClientPort
from apps.agent_harness.src.application.session_loop.types import (
    AgentRequest,
    AgentResponse,
    AgentTextResponse,
    AgentToolCallResponse,
    HarnessChunk,
    ModelRequest,
    ToolCallResult,
    ToolDecision,
)
from apps.agent_harness.src.application.session_loop.errors import (
    SessionLoopProviderFailureError,
)
from .errors import (
    ProviderAuthError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from .types import GatewayConfig
from .schemas import (
    ModelClientRequest,
    ModelClientChatMessage,
    StreamChunk,
    LLMToolCall,
    LLMResponse,
    ChatResponse,
)

import httpx
import json


class GatewayModelClient(ModelClientPort):
    def __init__(self, config: GatewayConfig) -> None:
        self._config = config

    def stream(self, payload: ModelRequest) -> Iterable[HarnessChunk]:
        request_body = ModelClientRequest(
            model=self._config.model,
            messages=[
                ModelClientChatMessage(role=m.role, content=m.content)
                for m in payload.messages
            ],
        )

        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            try:
                with httpx.Client(timeout=self._config.timeout_seconds) as client:
                    with client.stream(
                        "POST",
                        self._config.endpoint,
                        headers=headers,
                        json=request_body.model_dump(mode="json"),
                    ) as resp:
                        if resp.status_code in (401, 403):
                            raise ProviderAuthError(
                                details={"status_code": str(resp.status_code)}
                            )
                        if resp.status_code >= 400:
                            raise ProviderResponseError(
                                details={"status_code": str(resp.status_code)}
                            )

                        for line in resp.iter_lines():
                            if not line:
                                continue
                            if not line.startswith("data:"):
                                continue

                            data = line.removeprefix("data:").strip()
                            if data == "[DONE]":
                                break

                            try:
                                chunk = StreamChunk.model_validate_json(data)
                            except (ValidationError, json.JSONDecodeError) as exc:
                                raise ProviderResponseError(
                                    message="Malformed provider stream chunk",
                                    details={
                                        "raw_chunk": data[:500],
                                        "error": str(exc),
                                    },
                                ) from exc

                            delta = (
                                chunk.choices[0].delta.content
                                if chunk.choices
                                else None
                            )
                            if delta:
                                yield HarnessChunk(content=delta, final=False)

                yield HarnessChunk(content="", final=True)
            except httpx.TimeoutException as exc:
                raise ProviderTimeoutError(details={"error": str(exc)}) from exc
            except httpx.HTTPError as exc:
                raise ProviderUnavailableError(details={"error": str(exc)}) from exc

        except ProviderTimeoutError as exc:
            raise SessionLoopProviderFailureError(
                message="Provider request timed out", details=exc.details
            ) from exc
        except ProviderUnavailableError as exc:
            raise SessionLoopProviderFailureError(
                message="Provider unavailable", details=exc.details
            ) from exc
        except ProviderAuthError as exc:
            raise SessionLoopProviderFailureError(
                message="Provider authentication failed", details=exc.details
            ) from exc
        except ProviderResponseError as exc:
            raise SessionLoopProviderFailureError(
                message="Provider returned invalid response", details=exc.details
            ) from exc
        except Exception as exc:
            raise SessionLoopProviderFailureError(
                message="Model provider request failed", details={"error": str(exc)}
            ) from exc

    def complete(self, payload: ModelRequest) -> str:
        # TODO(mvp): Replace this stream-aggregation fallback with a true
        # non-streaming provider request to avoid duplicated work per turn.
        collected: list[str] = []
        for chunk in self.stream(payload=payload):
            if chunk.content:
                collected.append(chunk.content)
        return "".join(collected)

    def decide_tool_or_text(self, payload: ModelRequest) -> ToolDecision:
        request_body = ModelClientRequest(
            model=self._config.model,
            messages=[
                ModelClientChatMessage(role=m.role, content=m.content)
                for m in payload.messages
            ],
        )

        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            with httpx.Client(timeout=self._config.timeout_seconds) as client:
                resp = client.post(
                    self._config.endpoint,
                    headers=headers,
                    json={
                        **request_body.model_dump(mode="json"),
                        "stream": False,
                        "temperature": 0,
                        "response_format": {"type": "json_object"},
                    },
                )

            if resp.status_code in (401, 403):
                raise ProviderAuthError(details={"status_code": str(resp.status_code)})
            if resp.status_code >= 400:
                raise ProviderResponseError(
                    details={"status_code": str(resp.status_code)}
                )

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            adapter: TypeAdapter[LLMResponse] = TypeAdapter(LLMResponse)
            parsed = adapter.validate_json(content)

            if isinstance(parsed, LLMToolCall):
                return ToolDecision(
                    kind="tool_call",
                    tool_name=parsed.tool_name,
                    args=parsed.args,
                    text=None,
                )

            return ToolDecision(
                kind="text",
                tool_name=None,
                args={},
                text=parsed.text if parsed.text and parsed.text.strip() else None,
            )

        except httpx.TimeoutException as exc:
            raise SessionLoopProviderFailureError(
                message="Provider request timed out", details={"error": str(exc)}
            ) from exc
        except httpx.HTTPError as exc:
            raise SessionLoopProviderFailureError(
                message="Provider unavailable", details={"error": str(exc)}
            ) from exc
        except (KeyError, json.JSONDecodeError, TypeError, ValidationError):
            return ToolDecision(kind="text", tool_name=None, args={}, text=None)

    def agent_chat(self, payload: AgentRequest) -> AgentResponse:
        tools_payload: list[dict[str, object]] = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in payload.tools
        ]

        request_body = ModelClientRequest(
            model=self._config.model,
            messages=[
                ModelClientChatMessage(role=m.role, content=m.content)
                for m in payload.messages
            ],
            stream=False,
            tools=tools_payload,
        )

        headers = {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }

        body = request_body.model_dump(mode="json", exclude_none=True)
        body["tool_choice"] = "auto"

        try:
            with httpx.Client(timeout=self._config.timeout_seconds) as client:
                resp = client.post(
                    self._config.endpoint,
                    headers=headers,
                    json=body,
                )

            if resp.status_code in (401, 403):
                raise ProviderAuthError(details={"status_code": str(resp.status_code)})
            if resp.status_code >= 400:
                raise ProviderResponseError(
                    details={"status_code": str(resp.status_code)}
                )

            parsed = ChatResponse.model_validate(resp.json())
            message = parsed.choices[0].message

            if message.tool_calls:
                return AgentToolCallResponse(
                    tool_calls=[
                        ToolCallResult(
                            call_id=tc.id,
                            tool_name=tc.function.name,
                            args=json.loads(tc.function.arguments),
                        )
                        for tc in message.tool_calls
                    ]
                )

            return AgentTextResponse(content=message.content or "")

        except httpx.TimeoutException as exc:
            raise SessionLoopProviderFailureError(
                message="Provider request timed out", details={"error": str(exc)}
            ) from exc
        except httpx.HTTPError as exc:
            raise SessionLoopProviderFailureError(
                message="Provider unavailable", details={"error": str(exc)}
            ) from exc
        except (KeyError, IndexError, json.JSONDecodeError, ValidationError) as exc:
            raise SessionLoopProviderFailureError(
                message="Provider returned invalid agent response",
                details={"error": str(exc)},
            ) from exc
