from typing import Iterable

from apps.agent_harness.src.application.session_loop.ports import ModelClientPort
from apps.agent_harness.src.application.session_loop.types import (
    AgentRequest,
    AgentResponse,
    AgentTextResponse,
    HarnessChunk,
    ModelRequest,
    ToolDecision,
)


class LocalV1ModelClient(ModelClientPort):
    def stream(self, payload: ModelRequest) -> Iterable[HarnessChunk]:
        user_prompt = next(
            (m.content for m in payload.messages if m.role == "user"),
            "",
        )
        yield HarnessChunk(content="I can help with that. ", final=False)
        yield HarnessChunk(content=f"You asked: {user_prompt}", final=True)

    def complete(self, payload: ModelRequest) -> str:
        user_prompt = next(
            (m.content for m in payload.messages if m.role == "user"),
            "",
        )
        return f"I can help with that. You asked: {user_prompt}"

    def decide_tool_or_text(self, payload: ModelRequest) -> ToolDecision:
        _ = payload
        return ToolDecision(kind="text", tool_name=None, args={}, text=None)

    def agent_chat(self, payload: AgentRequest) -> AgentResponse:
        user_prompt = next(
            (m.content for m in payload.messages if m.role == "user"),
            "",
        )
        return AgentTextResponse(
            content=f"I can help with that. You asked: {user_prompt}"
        )
