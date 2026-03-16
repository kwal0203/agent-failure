from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Literal


ServerMessageType = Literal[
    "SESSION_STATUS", "AGENT_TEXT_CHUNK", "TRACE_EVENT", "POLICY_DENIAL", "SYSTEM_ERROR"
]


class SessionStatusPayload(BaseModel):
    state: str
    runtime_substate: str | None
    interactive: bool


class UserPromptPayload(BaseModel):
    content: str


class UserPromptMessage(BaseModel):
    type: Literal["USER_PROMPT"]
    session_id: UUID
    timestamp: datetime
    payload: UserPromptPayload


class PolicyDenialPayload(BaseModel):
    reason_code: str
    message: str


class AgentTextChunkPayload(BaseModel):
    content: str
    final: bool


class TraceEventPayload(BaseModel):
    event_code: str
    message: str


class SystemErrorPayload(BaseModel):
    error_code: str
    message: str


ServerPayload = (
    SessionStatusPayload
    | AgentTextChunkPayload
    | PolicyDenialPayload
    | TraceEventPayload
    | SystemErrorPayload
)


class ServerMessageEnvelope(BaseModel):
    type: ServerMessageType
    session_id: UUID
    timestamp: datetime
    payload: ServerPayload
    event_index: int | None = None
    request_id: UUID | None = None
    correlation_id: UUID | None = None
    final: bool | None = None
