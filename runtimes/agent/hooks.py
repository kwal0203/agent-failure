from __future__ import annotations

from typing import Protocol

from .types import AgentTurnItem, ToolCall, ToolResult
from .tools import ToolCtx


class AgentLabHooks(Protocol):
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
    def on_tool_dispatch(
        self, call: ToolCall, result: ToolResult, ctx: ToolCtx
    ) -> list[AgentTurnItem]:
        return []

    def on_text_output(self, text: str) -> list[AgentTurnItem]:
        return []

    def seed(self, ctx: ToolCtx) -> None:
        pass
