from __future__ import annotations

from typing import Protocol

from .types import AgentTurnItem, ChatMessage, ToolCall, ToolResult
from .tools import ToolCtx


class AgentLabHooks(Protocol):
    def pre_turn(
        self,
        ctx: ToolCtx,
        prompt: str,
    ) -> list[AgentTurnItem]:
        """Called once at turn start. Return emitted items and optionally short-circuit the turn."""
        ...

    def pre_model_call(
        self,
        ctx: ToolCtx,
        messages: list[ChatMessage],
    ) -> list[AgentTurnItem]:
        """Called before each model call. Return emitted items and optionally short-circuit the turn."""
        ...

    def on_tool_dispatch(
        self,
        call: ToolCall,
        result: ToolResult,
        ctx: ToolCtx,
    ) -> list[AgentTurnItem]:
        """Called after each tool dispatch. Return additional items to emit."""
        ...

    def on_text_output(
        self,
        text: str,
    ) -> list[AgentTurnItem]:
        """Called when the agent produces text output. Return additional items (e.g., TokenDisclosedEvent)."""
        ...

    def seed(
        self,
        ctx: ToolCtx,
    ) -> None:
        """Called once per session to seed initial state."""
        ...


class NullAgentLabHooks:
    def pre_turn(self, ctx: ToolCtx, prompt: str) -> list[AgentTurnItem]:
        _ = ctx
        _ = prompt
        return []

    def pre_model_call(
        self, ctx: ToolCtx, messages: list[ChatMessage]
    ) -> list[AgentTurnItem]:
        _ = ctx
        _ = messages
        return []

    def on_tool_dispatch(
        self, call: ToolCall, result: ToolResult, ctx: ToolCtx
    ) -> list[AgentTurnItem]:
        return []

    def on_text_output(self, text: str) -> list[AgentTurnItem]:
        return []

    def seed(self, ctx: ToolCtx) -> None:
        pass
