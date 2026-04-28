from __future__ import annotations

from uuid import UUID
from typing import Literal, Mapping
from dataclasses import dataclass, field
from apps.contracts.src.types import ToolName


FailureCode = Literal["provider_failure", "invalid_request", "internal_error"]
MessageRole = Literal["system", "user", "assistant", "tool"]


def default_parameters() -> dict[str, object]:
    return {}


@dataclass(frozen=True)
class HarnessTurnInput:
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    prompt: str


@dataclass(frozen=True)
class ToolCallMessage:
    call_id: str
    tool_name: str
    arguments: str


@dataclass(frozen=True)
class ChatMessage:
    role: MessageRole
    content: str
    tool_call_id: str | None = None
    tool_calls: list[ToolCallMessage] | None = None


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
    urgency_marker: bool | None = None
    source: Literal["learner", "system"] = "learner"


@dataclass(frozen=True)
class ToolDecision:
    kind: Literal["tool_call", "text"]
    tool_name: ToolName | None
    args: dict[str, str]
    text: str | None


@dataclass(frozen=True)
class DeleteFileResult:
    deleted: bool
    exists_after: bool


@dataclass(frozen=True)
class ReadFileResult:
    content: str | None
    error_code: str | None = None


@dataclass(frozen=True)
class WriteFileResult:
    path: str
    bytes_written: int


MemoryType = Literal[
    "user_workflow_preferences",
    "vendor_profile_memory",
    "exception_handling_memory",
]
ProvenanceTrust = Literal["trusted", "untrusted"]


@dataclass(frozen=True)
class VendorMasterRecord:
    vendor_id: str
    vendor_name: str
    official_account: str
    routing_number: str
    status: str
    last_verified: str


@dataclass(frozen=True)
class AttackerTargetRecord:
    vendor_id: str
    vendor_name: str
    attacker_account: str
    routing_number: str


@dataclass(frozen=True)
class InvoiceRecord:
    invoice_id: str
    vendor_id: str
    vendor_name: str
    amount: float
    currency: str


@dataclass(frozen=True)
class MemoryRecord:
    memory_type: MemoryType
    content: str
    metadata: dict[str, str]
    source_artifact_id: str
    source_artifact_type: str
    provenance_trust: ProvenanceTrust
    stored_at: str


@dataclass(frozen=True)
class WriteMemoryInput:
    memory_type: MemoryType
    content: str
    metadata: dict[str, str]
    source_artifact_id: str
    source_artifact_type: str
    provenance_trust: ProvenanceTrust
    stored_at: str


@dataclass(frozen=True)
class ToolDefinition:
    name: str
    description: str
    parameters: Mapping[str, object] = field(default_factory=default_parameters)


@dataclass(frozen=True)
class ToolCallResult:
    call_id: str
    tool_name: str
    args: dict[str, str | int | float | bool | None]


@dataclass(frozen=True)
class AgentRequest:
    messages: list[ChatMessage]
    tools: list[ToolDefinition]


@dataclass(frozen=True)
class AgentTextResponse:
    content: str


@dataclass(frozen=True)
class AgentToolCallResponse:
    tool_calls: list[ToolCallResult]


AgentResponse = AgentTextResponse | AgentToolCallResponse
