from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime


class MarkSessionHintsSeenResponse(BaseModel):
    session_id: UUID
    updated_count: int


class MarkSessionFeedbackSeenResponse(BaseModel):
    session_id: UUID
    updated_count: int


class StopSessionResponse(BaseModel):
    session_id: UUID
    accepted: bool = True
    state: str


class SessionResponse(BaseModel):
    id: UUID
    lab_id: UUID
    # TODO: Make lab_version_id non-null once lab version binding is implemented in create flow.
    lab_version_id: UUID | None
    lab_difficulty: str
    state: str
    resume_mode: str
    created_at: datetime


class CreateSessionResponse(BaseModel):
    session: SessionResponse


class CreateSessionRequest(BaseModel):
    lab_id: UUID
    lab_difficulty: str = "medium"


class InjectSessionEmailResponse(BaseModel):
    session_id: UUID
    email_id: str | None = None
    accepted: bool = True


class LearnerExplanationRequest(BaseModel):
    explanation: str = Field(min_length=20, max_length=2048)


class LearnerExplanationResponse(BaseModel):
    session_id: UUID
    explanation_id: UUID
    accepted: bool = True
