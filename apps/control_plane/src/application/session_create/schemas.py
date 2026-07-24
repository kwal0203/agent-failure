from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class CreateSessionResult(BaseModel):
    session_id: UUID
    lab_id: UUID
    # Nullable for compatibility with sessions created before version binding
    # became mandatory. New sessions always carry an active lab version.
    lab_version_id: UUID | None
    state: str
    resume_mode: str
    created_at: datetime
    requester_user_id: UUID


class DecisionDetails(BaseModel):
    current: int
    quota: int
    limit: int
