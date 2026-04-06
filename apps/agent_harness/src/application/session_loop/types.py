from uuid import UUID
from typing import Literal
from dataclasses import dataclass


FailureCode = Literal["provider_failure", "invalid_request", "internal_error"]
MessageRole = Literal["system", "user", "assistant", "tool"]


@dataclass(frozen=True)
class HarnessTurnInput:
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    prompt: str


@dataclass(frozen=True)
class ChatMessage:
    role: MessageRole
    content: str


@dataclass(frozen=True)
class ModelRequest:
    messages: list[ChatMessage]


@dataclass(frozen=True)
class HarnessChunk:
    content: str
    final: bool


@dataclass(frozen=True)
class HarnessFailure:
    code: FailureCode
    message: str
    details: dict[str, str] | None


@dataclass(frozen=True)
class HarnessTurnResult:
    chunks: list[HarnessChunk]
    failure: HarnessFailure | None = None


@dataclass(frozen=True)
class InboxItem:
    email_id: str
    email_from: str
    email_subject: str
    email_body: str
    email_preview: str | None = None
    malicious: bool | None = None
    source: Literal["learner"] = "learner"


@dataclass(frozen=True)
class ToolDecision:
    kind: Literal["tool_call", "text"]
    tool_name: Literal["list_inbox", "read_email"] | None
    args: dict[str, str]
    text: str | None
