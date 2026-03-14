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
