from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


ServerMessageType = Literal[
    "SESSION_STATUS",
    "AGENT_TEXT_CHUNK",
    "TRACE_EVENT",
    "POLICY_DENIAL",
    "SYSTEM_ERROR",
    "USER_PROMPT",
    "LEARNER_FEEDBACK",
]
LearnerStatusType = Literal["learned", "progress", "no_progress", "session_terminal"]


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


class LearnerFeedbackItem(BaseModel):
    status: LearnerStatusType
    reason_code: str
    evidence_snippet: str


class LearnerFeedbackPayload(BaseModel):
    feedback: list[LearnerFeedbackItem]


ServerPayload = (
    SessionStatusPayload
    | AgentTextChunkPayload
    | PolicyDenialPayload
    | TraceEventPayload
    | SystemErrorPayload
    | UserPromptPayload
    | LearnerFeedbackPayload
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


def build_policy_denial_message(
    session_id: UUID,
    reason_code: str,
    message: str,
    *,
    request_id: UUID | None = None,
    correlation_id: UUID | None = None,
    event_index: int | None = None,
) -> ServerMessageEnvelope:
    return ServerMessageEnvelope(
        type="POLICY_DENIAL",
        session_id=session_id,
        timestamp=datetime.now(timezone.utc),
        payload=PolicyDenialPayload(reason_code=reason_code, message=message),
        request_id=request_id,
        correlation_id=correlation_id,
        event_index=event_index,
        final=True,
    )


def build_agent_text_chunk_message(
    session_id: UUID,
    chunk: str,
    final: bool,
    *,
    request_id: UUID | None = None,
    correlation_id: UUID | None = None,
    event_index: int | None = None,
) -> ServerMessageEnvelope:
    return ServerMessageEnvelope(
        type="AGENT_TEXT_CHUNK",
        session_id=session_id,
        timestamp=datetime.now(timezone.utc),
        payload=AgentTextChunkPayload(content=chunk, final=final),
        request_id=request_id,
        correlation_id=correlation_id,
        event_index=event_index,
    )


def build_session_status_message(
    session_id: UUID,
    state: str,
    runtime_substate: str | None,
    interactive: bool,
    *,
    request_id: UUID | None = None,
    correlation_id: UUID | None = None,
    event_index: int | None = None,
) -> ServerMessageEnvelope:
    return ServerMessageEnvelope(
        type="SESSION_STATUS",
        session_id=session_id,
        timestamp=datetime.now(timezone.utc),
        payload=SessionStatusPayload(
            state=state, runtime_substate=runtime_substate, interactive=interactive
        ),
        request_id=request_id,
        correlation_id=correlation_id,
        event_index=event_index,
    )


def build_trace_event_message(
    session_id: UUID,
    event_code: str,
    message: str,
    *,
    request_id: UUID | None = None,
    correlation_id: UUID | None = None,
    event_index: int | None = None,
) -> ServerMessageEnvelope:
    return ServerMessageEnvelope(
        type="TRACE_EVENT",
        session_id=session_id,
        timestamp=datetime.now(timezone.utc),
        payload=TraceEventPayload(event_code=event_code, message=message),
        request_id=request_id,
        correlation_id=correlation_id,
        event_index=event_index,
    )


def build_system_error_message(
    session_id: UUID,
    error_code: str,
    message: str,
    *,
    request_id: UUID | None = None,
    correlation_id: UUID | None = None,
    event_index: int | None = None,
) -> ServerMessageEnvelope:
    return ServerMessageEnvelope(
        type="SYSTEM_ERROR",
        session_id=session_id,
        timestamp=datetime.now(timezone.utc),
        payload=SystemErrorPayload(error_code=error_code, message=message),
        request_id=request_id,
        correlation_id=correlation_id,
        event_index=event_index,
    )
