from pydantic import BaseModel, Field
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


RuntimeStreamEventType = (
    TurnStartedEvent | TextChunkEvent | TurnCompletedEvent | TurnFailedEvent
)

RuntimeStreamEvent = Annotated[
    TurnStartedEvent | TextChunkEvent | TurnCompletedEvent | TurnFailedEvent,
    Field(discriminator="type"),
]
