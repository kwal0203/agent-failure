from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Literal, Any


EvaluatorFeedbackStatusType = Literal[
    "learned", "progress", "no_progress", "session_terminal"
]
TraceFamilyType = Literal["lifecycle", "learner", "runtime", "tool", "model"]


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


class MarkSessionHintsSeenResponse(BaseModel):
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
    provisioning_stalled: bool = False
    provisioning_stall_reason_code: str | None
    progress_chips: list[SessionProgressChipResponse] = []
    hints: list[SessionHintResponse] = []
    unread_hint_count: int = 0


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


class LabCapabilitiesResponse(BaseModel):
    supports_resume: bool
    supports_uploads: bool


class LabCatalogItemResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    summary: str
    capabilities: LabCapabilitiesResponse


class GetLabsResponse(BaseModel):
    labs: list[LabCatalogItemResponse]


class EvaluatorFeedbackResponse(BaseModel):
    status: EvaluatorFeedbackStatusType
    reason_code: str
    evidence_snippet: str


class GetFeedbackResponse(BaseModel):
    feedback: tuple[EvaluatorFeedbackResponse, ...]


class SessionTraceEvent(BaseModel):
    id: UUID
    event_index: int
    family: TraceFamilyType
    event_type: str
    source: str
    occurred_at: datetime
    payload: dict[str, Any]


class GetSessionTraceResponse(BaseModel):
    events: tuple[SessionTraceEvent, ...]
    next_cursor: str | None = None


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
