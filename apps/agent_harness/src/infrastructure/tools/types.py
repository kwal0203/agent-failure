from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ToolCallDecision:
    kind: Literal["tool_call"]
    tool_name: Literal["list_inbox", "read_email"]
    args: dict[str, str]


@dataclass(frozen=True)
class TextDecision:
    kind: Literal["text"]
    text: str
