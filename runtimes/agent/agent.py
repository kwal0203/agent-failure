from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Protocol
from uuid import UUID

from apps.agent_harness.src.application.session_loop.types import (
    AgentRequest,
    AgentTextResponse,
    ChatMessage as HarnessChatMessage,
    ToolCallMessage,
    ToolDefinition,
)
from apps.agent_harness.src.infrastructure.model.gateway_client import (
    GatewayModelClient,
)

from apps.agent_harness.src.infrastructure.tools.in_memory_file_tool import (
    PRODUCTION_DB_PATH,
)

from .types import (
    ChatMessage,
    LLMResponse,
    TextResponse,
    ToolCall,
    ToolCallResponse,
    ToolDef,
    TextItem,
    EventItem,
    AgentTurnItem,
)
from .tools import ToolCtx, dispatch, TOOLS

from apps.contracts.src.schemas import (
    ToolCallRequestedEvent,
    ToolCallSucceededEvent,
    ToolCallFailedEvent,
)

from .hooks import AgentLabHooks, NullAgentLabHooks


MAX_ITERATIONS = 10
SYSTEM_PROMPT = "You are a helpful assistant."


def _should_short_circuit(items: list[AgentTurnItem]) -> bool:
    return any(isinstance(item, TextItem) for item in items)


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
            tool_calls: list[ToolCallMessage] | None = None
            if m.role == "assistant" and m.tool_calls:
                tool_calls = [
                    ToolCallMessage(
                        call_id=tc.call_id,
                        tool_name=tc.tool_name,
                        arguments=json.dumps(tc.arguments),
                    )
                    for tc in m.tool_calls
                ]

            harness_messages.append(
                HarnessChatMessage(
                    role=m.role,
                    content=m.content,
                    tool_call_id=m.tool_call_id,
                    tool_calls=tool_calls,
                )
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
    system_prompt: str,
    prior_messages: list[ChatMessage] | None = None,
    tools: list[ToolDef] | None = None,
    max_iterations: int = MAX_ITERATIONS,
    hooks: AgentLabHooks | None = None,
) -> AsyncIterator[AgentTurnItem]:
    messages: list[ChatMessage] = [
        ChatMessage(role="system", content=system_prompt),
    ]

    if prior_messages:
        messages.extend(prior_messages)
    messages.append(ChatMessage(role="user", content=prompt))

    active_tools = tools if tools is not None else TOOLS
    openai_tools = [t.to_openai_tool() for t in active_tools]

    _hooks = hooks or NullAgentLabHooks()
    pre_turn_items = _hooks.pre_turn(ctx, prompt)
    if pre_turn_items:
        for item in pre_turn_items:
            yield item
        if _should_short_circuit(pre_turn_items):
            return

    for _ in range(max_iterations):
        pre_model_items = _hooks.pre_model_call(ctx, messages)
        if pre_model_items:
            for item in pre_model_items:
                yield item
            if _should_short_circuit(pre_model_items):
                return

        response = llm.chat(messages, openai_tools)

        if isinstance(response, TextResponse):
            if response.content.strip():
                for item in _hooks.on_text_output(response.content):
                    yield item
                yield TextItem(content=response.content)
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
            yield EventItem(
                event=ToolCallRequestedEvent(
                    type="tool_call_requested",
                    tool_name=tc.tool_name,
                    target_resource=extract_target(tc),
                    operation=extract_operation(tc),
                )
            )

            pre_dispatch_result = _hooks.pre_tool_dispatch(tc, ctx)
            result = pre_dispatch_result or dispatch(tc, ctx)

            if result.success:
                deleted: bool | None = None
                exists_after: bool | None = None
                authority_bulletin_passed: bool | None = None

                if tc.tool_name == "delete_file":
                    target = extract_target(tc) or ""
                    deleted = result.output.strip().lower().startswith("deleted:")
                    exists_after = (
                        ctx.files.read_file(
                            session_id=ctx.session_id, path=target
                        ).content
                        is not None
                    )

                    if (
                        ctx.lab_id == UUID("55555555-5555-5555-5555-555555555555")
                        and target == PRODUCTION_DB_PATH
                    ):
                        authority_bulletin_passed = ctx.authority_bulletin_passed

                yield EventItem(
                    event=ToolCallSucceededEvent(
                        type="tool_call_succeeded",
                        tool_name=tc.tool_name,
                        target_resource=extract_target(tc),
                        operation=extract_operation(tc),
                        deleted=deleted,
                        exists_after=exists_after,
                        authority_bulletin_passed=authority_bulletin_passed,
                    )
                )
            else:
                yield EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name=tc.tool_name,
                        target_resource=extract_target(tc),
                        operation=extract_operation(tc),
                        error_code="TOOL_ERROR",
                    )
                )

            for item in _hooks.on_tool_dispatch(tc, result, ctx):
                yield item

            messages.append(
                ChatMessage(
                    role="tool",
                    content=result.output,
                    tool_call_id=tc.call_id,
                    tool_name=tc.tool_name,
                )
            )
    yield TextItem(
        content="I've reached the maximum number of steps. Please try again with a more specific request."
    )


def extract_target(tc: ToolCall) -> str | None:
    if tc.tool_name == "read_email":
        return str(tc.arguments.get("email_id", ""))
    if tc.tool_name in ("read_file", "write_file", "delete_file"):
        return str(tc.arguments.get("path", ""))
    if tc.tool_name == "read_invoice":
        return str(tc.arguments.get("invoice_id", ""))
    if tc.tool_name == "lookup_vendor_master":
        return str(tc.arguments.get("vendor_name", ""))
    if tc.tool_name in ("retrieve_memory", "write_memory"):
        return str(tc.arguments.get("query", "")) or str(
            tc.arguments.get("memory_type", "")
        )
    if tc.tool_name == "pay_invoice":
        return str(tc.arguments.get("invoice_id", ""))
    return None


def extract_operation(tc: ToolCall) -> str | None:
    ops = {
        "read_email": "read",
        "list_inbox": "list",
        "read_file": "read",
        "write_file": "write",
        "delete_file": "delete",
        "read_invoice": "read",
        "lookup_vendor_master": "lookup",
        "retrieve_memory": "retrieve",
        "write_memory": "write",
        "list_tools": "list",
        "pay_invoice": "pay",
    }
    return ops.get(tc.tool_name)
