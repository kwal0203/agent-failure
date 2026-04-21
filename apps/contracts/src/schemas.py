from pydantic import BaseModel, Field, field_validator, ConfigDict
from uuid import UUID
from typing import Literal, Annotated


ErrorCode = Literal["provider_failure", "invalid_request", "internal_error"]


# Dataclasses for non-streaming


class RunTurnRequest(BaseModel):
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    turn_id: UUID
    prompt: str
    idempotency_key: str | None = None


class RunTurnResponse(BaseModel):
    turn_id: UUID
    status: Literal["completed", "failed"]
    output_text: str
    chunks_emitted: int
    duration_ms: int
    model_provider: str | None = None
    model_name: str | None = None


class RunTurnErrorResponse(BaseModel):
    turn_id: UUID
    error_code: ErrorCode
    message: str
    retryable: bool
    details: dict[str, object] | None = None


# Dataclasses for streaming


class RunTurnStreamRequest(BaseModel):
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    turn_id: UUID
    prompt: str
    idempotency_key: str | None = None


class TurnStartedEvent(BaseModel):
    type: Literal["turn_started"]


class TextChunkEvent(BaseModel):
    type: Literal["text_chunk"]
    content: str
    chunk_index: int
    final: bool


class TurnCompletedEvent(BaseModel):
    type: Literal["turn_completed"]
    duration_ms: int
    chunks_emitted: int


class TurnFailedEvent(BaseModel):
    type: Literal["turn_failed"]
    error_code: str
    message: str
    retryable: bool


# Runtime events (prompt-injection lab)


class AttackEmailSentEvent(BaseModel):
    type: Literal["attack_email_sent"]
    recipient: str
    subject: str
    email_id: str | None = None


class MaliciousEmailReadEvent(BaseModel):
    type: Literal["malicious_email_read"]
    subject: str
    malicious_marker: bool
    email_id: str | None = None


class TokenDisclosureAttemptedEvent(BaseModel):
    type: Literal["token_disclosure_attempted"]
    channel: str
    target: str


class TokenDisclosedEvent(BaseModel):
    type: Literal["token_disclosed"]
    channel: str
    token_kind: str


class ToolCallRequestedEvent(BaseModel):
    type: Literal["tool_call_requested"]
    tool_name: str
    target_resource: str | None = None
    command: str | None = None
    operation: str | None = None
    memory_type: str | None = None
    provenance_trust: str | None = None
    source_artifact_id: str | None = None
    source_artifact_type: str | None = None
    invoice_id: str | None = None
    vendor_name: str | None = None
    vendor_id: str | None = None
    amount: float | None = None
    account_number: str | None = None
    retrieved_memory_references: list[str] | None = None


class ToolCallSucceededEvent(BaseModel):
    type: Literal["tool_call_succeeded"]
    tool_name: str
    target_resource: str | None = None
    command: str | None = None
    operation: str | None = None
    deleted: bool | None = None
    exists_after: bool | None = None
    memory_type: str | None = None
    provenance_trust: str | None = None
    source_artifact_id: str | None = None
    source_artifact_type: str | None = None
    invoice_id: str | None = None
    vendor_name: str | None = None
    vendor_id: str | None = None
    amount: float | None = None
    account_number: str | None = None
    retrieved_memory_references: list[str] | None = None


class ToolCallFailedEvent(BaseModel):
    type: Literal["tool_call_failed"]
    tool_name: str
    target_resource: str | None = None
    command: str | None = None
    operation: str | None = None
    error_code: str | None = None
    memory_type: str | None = None
    provenance_trust: str | None = None
    source_artifact_id: str | None = None
    source_artifact_type: str | None = None
    invoice_id: str | None = None
    vendor_name: str | None = None
    vendor_id: str | None = None
    amount: float | None = None
    account_number: str | None = None
    retrieved_memory_references: list[str] | None = None


RuntimeStreamEventType = (
    TurnStartedEvent | TextChunkEvent | TurnCompletedEvent | TurnFailedEvent
)

RuntimeStreamEvent = Annotated[
    TurnStartedEvent
    | TextChunkEvent
    | TurnCompletedEvent
    | TurnFailedEvent
    | AttackEmailSentEvent
    | MaliciousEmailReadEvent
    | TokenDisclosureAttemptedEvent
    | TokenDisclosedEvent
    | ToolCallRequestedEvent
    | ToolCallSucceededEvent
    | ToolCallFailedEvent,
    Field(discriminator="type"),
]


class EmailArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email_from: str = Field(min_length=1, max_length=64)
    email_subject: str = Field(min_length=1, max_length=64)
    email_body: str = Field(min_length=1, max_length=256)
    email_preview: str | None = None
    email_id: str | None = None
    malicious: bool | None = None
    source: Literal["learner"] = "learner"

    @field_validator(
        "email_from", "email_subject", "email_body", "email_id", mode="before"
    )
    @classmethod
    def _strip_strings(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v


class ExplanationArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    explanation: str = Field(min_length=20, max_length=2048)
    source: Literal["learner"] = "learner"

    @field_validator("explanation", mode="before")
    @classmethod
    def _strip_strings(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v


class ApiError(BaseModel):
    code: str
    message: str
    retryable: bool
    details: dict[str, object] | None


class ApiErrorEnvelope(BaseModel):
    error: ApiError
