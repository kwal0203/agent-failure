from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class CreateSessionResult(BaseModel):
    session_id: UUID
    lab_id: UUID
    # TODO: Make lab_version_id non-null once lab version binding is implemented in create flow.
    lab_version_id: UUID | None
    state: str
    resume_mode: str
    created_at: datetime
    requester_user_id: UUID
