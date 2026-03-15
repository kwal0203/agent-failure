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
