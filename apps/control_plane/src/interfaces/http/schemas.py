from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Literal

from apps.control_plane.src.application.session_query.types import CompletionStatus


class SessionProgressChipResponse(BaseModel):
    objective_key: str
    label: str
    status: Literal["pending", "complete"]
    completed_at: datetime | None
    updated_at: datetime


class SessionHintResponse(BaseModel):
    hint_key: str
    text: str
    sort_order: int
    status: Literal["pending", "unlocked"]
    unlock_at: datetime
    unlocked_at: datetime | None
    seen_at: datetime | None


class SessionFeedbackResponse(BaseModel):
    id: UUID
    feedback_key: str
    reason_code: str
    message: str
    severity: Literal["info", "warning", "error"]
    trigger_event_index: int | None
    created_at: datetime
    seen_at: datetime | None


class SessionRuntimeFileResponse(BaseModel):
    path: str
    content: str
    updated_at: datetime


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


class SessionMetadataResponse(BaseModel):
    id: UUID
    lab_id: UUID | None
    lab_version_id: UUID | None
    lab_difficulty: str = "medium"
    state: str
    runtime_substate: str | None
    resume_mode: str
    last_transition_reason: str | None
    interactive: bool
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None
    completion_status: CompletionStatus = "in_progress"
    completed_at: datetime | None = None
    completion_reason_code: str | None = None
    provisioning_stalled: bool = False
    provisioning_stall_reason_code: str | None
    progress_chips: list[SessionProgressChipResponse] = []
    hints: list[SessionHintResponse] = []
    unread_hint_count: int = 0
    feedback_items: list[SessionFeedbackResponse] = []
    # Backward-compat alias; new clients should use feedback_items.
    feedback: list[SessionFeedbackResponse] = []
    unread_feedback_count: int = 0
    runtime_files: list[SessionRuntimeFileResponse] = []


class GetSessionMetadataResponse(BaseModel):
    session: SessionMetadataResponse


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
