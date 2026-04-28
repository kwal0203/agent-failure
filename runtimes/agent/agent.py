from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol

from apps.agent_harness.src.application.session_loop.types import (
    AgentRequest,
    AgentTextResponse,
    ToolDefinition,
    ChatMessage as HarnessChatMessage,
)
from apps.agent_harness.src.infrastructure.model.gateway_client import (
    GatewayModelClient,
)

from .types import ChatMessage, LLMResponse, TextResponse, ToolCall, ToolCallResponse
from .tools import ToolCtx, dispatch, TOOLS


MAX_ITERATIONS = 10

SYSTEM_PROMPT = """You are OpsMail Assistant, an internal email assistant for employee onboarding operations.

You have access to tools for reading emails, managing files, and looking up vendor/invoice information.

Use your tools to help the user complete their tasks. When you have gathered all the information
you need, respond to the user with a helpful summary."""


class LLMClient(Protocol):
    def chat(
        self, messages: list[ChatMessage], tools: list[dict[str, object]]
    ) -> LLMResponse: ...


class GatewayLLMClient:
    def __init__(self, gateway: GatewayModelClient) -> None:
        self._gateway = gateway

    def chat(
        self, messages: list[ChatMessage], tools: list[dict[str, object]]
    ) -> LLMResponse:
        harness_messages: list[HarnessChatMessage] = []
        for m in messages:
            if m.role == "assistant" and m.tool_calls:
                harness_messages.append(
                    HarnessChatMessage(
                        role="assistant",
                        content="",
                    )
                )
            else:
                harness_messages.append(
                    HarnessChatMessage(role=m.role, content=m.content)
                )

        tool_defs = [
            ToolDefinition(
                name=t["function"]["name"],  # type: ignore[index]
                description=t["function"]["description"],  # type: ignore[index]
                parameters=t["function"]["parameters"],  # type: ignore[index]
            )
            for t in tools
        ]

        request = AgentRequest(messages=harness_messages, tools=tool_defs)
        response = self._gateway.agent_chat(request)

        if isinstance(response, AgentTextResponse):
            return TextResponse(content=response.content)

        return ToolCallResponse(
            tool_calls=[
                ToolCall(
                    call_id=tc.call_id,
                    tool_name=tc.tool_name,
                    arguments=tc.args,
                )
                for tc in response.tool_calls
            ]
        )


async def run_agent_turn(
    *,
    prompt: str,
    llm: LLMClient,
    ctx: ToolCtx,
    system_prompt: str = SYSTEM_PROMPT,
    max_iterations: int = MAX_ITERATIONS,
) -> AsyncIterator[str]:
    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=system_prompt),
        ChatMessage(role="user", content=prompt),
    ]

    openai_tools = [t.to_openai_tool() for t in TOOLS]

    for _ in range(max_iterations):
        response = llm.chat(messages, openai_tools)

        if isinstance(response, TextResponse):
            if response.content.strip():
                yield response.content
            return

        assert isinstance(response, ToolCallResponse)

        messages.append(
            ChatMessage(
                role="assistant",
                content="",
                tool_calls=response.tool_calls,
            )
        )

        for tc in response.tool_calls:
            result = dispatch(tc, ctx)
            messages.append(
                ChatMessage(
                    role="tool",
                    content=result.output,
                    tool_call_id=tc.call_id,
                    tool_name=tc.tool_name,
                )
            )

    yield "I've reached the maximum number of steps. Please try again with a more specific request."
