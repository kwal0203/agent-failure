from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest

from runtimes.agent.types import ChatMessage, LLMResponse, TextResponse
from runtimes.agent.agent import LLMClient, run_agent_turn
from runtimes.agent.hooks import AgentLabHooks
from runtimes.agent.tools import ToolCtx, TOOLS
from runtimes.agent.types import ToolDef
from runtimes.agent.types import TextItem, EventItem
from .stubs import StubFiles, StubInbox, StubInvoiceMemory


def make_ctx(
    *,
    session_id: UUID | None = None,
    inbox: StubInbox | None = None,
    files: StubFiles | None = None,
    invoice: StubInvoiceMemory | None = None,
    available_tools: tuple[ToolDef, ...] | None = None,
) -> ToolCtx:
    return ToolCtx(
        session_id=session_id or uuid4(),
        inbox=inbox or StubInbox(),
        files=files or StubFiles(),
        invoice_memory=invoice or StubInvoiceMemory(),
        available_tools=available_tools or tuple(TOOLS),
    )


@pytest.fixture
def stub_inbox() -> StubInbox:
    return StubInbox()


@pytest.fixture
def ctx(stub_inbox: StubInbox) -> ToolCtx:
    # This fixture 'requests' the stub_inbox fixture
    # and uses it to build the context automatically
    return make_ctx(inbox=stub_inbox)


class ScriptedLLM(LLMClient):
    def __init__(self, responses: Sequence[LLMResponse]) -> None:
        self._responses = list(responses)
        self._call_index = 0
        self.calls: list[list[ChatMessage]] = []

    def chat(
        self, messages: list[ChatMessage], tools: list[dict[str, object]]
    ) -> LLMResponse:
        self.calls.append(messages)
        if self._call_index >= len(self._responses):
            return TextResponse(content="No more responses.")
        resp = self._responses[self._call_index]
        self._call_index += 1
        return resp


async def run_turn(
    *,
    prompt: str = "hello",
    llm: LLMClient,
    ctx: ToolCtx | None = None,
    hooks: AgentLabHooks | None = None,
    prior_messages: list[ChatMessage] | None = None,
) -> str:
    parts: list[str] = []
    async for item in run_agent_turn(
        prompt=prompt,
        llm=llm,
        ctx=ctx or make_ctx(),
        hooks=hooks,
        prior_messages=prior_messages,
    ):
        if isinstance(item, TextItem):
            parts.append(item.content)
    return "".join(parts)


async def run_turn_collect_events(
    *,
    prompt: str = "hello",
    llm: LLMClient,
    ctx: ToolCtx | None = None,
    hooks: AgentLabHooks | None = None,
    prior_messages: list[ChatMessage] | None = None,
) -> tuple[str, list[EventItem]]:
    text_parts: list[str] = []
    events: list[EventItem] = []
    async for item in run_agent_turn(
        prompt=prompt,
        llm=llm,
        ctx=ctx or make_ctx(),
        hooks=hooks,
        prior_messages=prior_messages,
    ):
        if isinstance(item, TextItem):
            text_parts.append(item.content)
        else:
            events.append(item)
    return "".join(text_parts), events
