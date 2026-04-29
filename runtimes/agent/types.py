from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

from apps.contracts.src.schemas import RuntimeStreamEvent


MessageRole = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True)
class ChatMessage:
    role: MessageRole
    content: str
    tool_call_id: str | None = None
    tool_name: str | None = None
    tool_calls: list[ToolCall] | None = None


@dataclass(frozen=True)
class ToolCall:
    call_id: str
    tool_name: str
    arguments: dict[str, str | int | float | bool | None]


@dataclass(frozen=True)
class ToolResult:
    call_id: str
    tool_name: str
    output: str
    success: bool = True


def _empty_schema() -> dict[str, object]:
    return {"type": "object", "properties": {}, "required": []}


@dataclass(frozen=True)
class ToolDef:
    name: str
    description: str
    parameters: dict[str, object] = field(default_factory=_empty_schema)

    def to_openai_tool(self) -> dict[str, object]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass(frozen=True)
class TurnInput:
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    turn_id: UUID
    prompt: str
    idempotency_key: str | None = None
    authority_bulletin_passed: bool | None = None


@dataclass(frozen=True)
class TextResponse:
    content: str


@dataclass(frozen=True)
class ToolCallResponse:
    tool_calls: list[ToolCall]


LLMResponse = TextResponse | ToolCallResponse


@dataclass(frozen=True)
class TextItem:
    content: str


@dataclass(frozen=True)
class EventItem:
    event: RuntimeStreamEvent


AgentTurnItem = TextItem | EventItem
