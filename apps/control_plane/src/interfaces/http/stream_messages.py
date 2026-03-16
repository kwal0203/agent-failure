from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Literal


class SessionStatusPayload(BaseModel):
    state: str
    runtime_substate: str | None
    interactive: bool


class SessionStatusMessage(BaseModel):
    type: Literal["SESSION_STATUS"] = "SESSION_STATUS"
    session_id: UUID
    timestamp: datetime
    payload: SessionStatusPayload


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


class PolicyDenialMessage(BaseModel):
    type: Literal["POLICY_DENIAL"]
    session_id: UUID
    timestamp: datetime
    payload: PolicyDenialPayload


class AgentTextChunkPayload(BaseModel):
    content: str
    final: bool


class AgentTextChunkMessage(BaseModel):
    type: Literal["AGENT_TEXT_CHUNK"]
    session_id: UUID
    timestamp: datetime
    payload: AgentTextChunkPayload
