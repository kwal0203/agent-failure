from pydantic import BaseModel, Field, field_validator, ConfigDict
from uuid import UUID
from typing import Literal, Annotated, Any
from datetime import datetime

from .types import (
    CompletionOutcome,
    FeedbackSeverity,
    OutboxEventName,
    SessionCompletedEventName,
    SessionFeedbackCreatedEventName,
    TraceFamily,
)


ErrorCode = Literal["provider_failure", "invalid_request", "internal_error"]
SessionCompletionStatus = Literal[
    "in_progress",
    "completed_success",
    "completed_failure",
]


# Dataclasses for non-streaming


class RunTurnRequest(BaseModel):
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    turn_id: UUID
    prompt: str
    idempotency_key: str | None = None
    authority_bulletin_passed: bool | None = None


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
    authority_bulletin_passed: bool | None = None


class TurnStartedEvent(BaseModel):
    type: Literal["turn_started"]
    runtime: str | None = None


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


# Runtime events (prompt-injection lab)


class AttackEmailSentEvent(BaseModel):
    type: Literal["attack_email_sent"]
    recipient: str
    subject: str
    email_id: str | None = None


class MaliciousEmailReadEvent(BaseModel):
    type: Literal["malicious_email_read"]
    subject: str
    malicious_marker: bool
    email_id: str | None = None


class TokenDisclosureAttemptedEvent(BaseModel):
    type: Literal["token_disclosure_attempted"]
    channel: str
    target: str


class TokenDisclosedEvent(BaseModel):
    type: Literal["token_disclosed"]
    channel: str
    token_kind: str


class TryAttackConsoleHintEvent(BaseModel):
    type: Literal["try_attack_console_hint"]
    message: str


class ToolCallRequestedEvent(BaseModel):
    type: Literal["tool_call_requested"]
    tool_name: str
    target_resource: str | None = None
    command: str | None = None
    operation: str | None = None
    memory_type: str | None = None
    provenance_trust: str | None = None
    source_artifact_id: str | None = None
    source_artifact_type: str | None = None
    invoice_id: str | None = None
    vendor_name: str | None = None
    vendor_id: str | None = None
    amount: float | None = None
    account_number: str | None = None
    retrieved_memory_references: list[str] | None = None
    qualifying_log: bool | None = None
    log_case: str | None = None


class ToolCallSucceededEvent(BaseModel):
    type: Literal["tool_call_succeeded"]
    tool_name: str
    target_resource: str | None = None
    command: str | None = None
    operation: str | None = None
    deleted: bool | None = None
    exists_after: bool | None = None
    authority_bulletin_passed: bool | None = None
    authority_bulletin_signer: str | None = None
    authority_bulletin_destructive_db_delete: bool | None = None
    authority_bulletin_runbook_action_type: str | None = None
    memory_type: str | None = None
    provenance_trust: str | None = None
    source_artifact_id: str | None = None
    source_artifact_type: str | None = None
    invoice_id: str | None = None
    vendor_name: str | None = None
    vendor_id: str | None = None
    amount: float | None = None
    account_number: str | None = None
    retrieved_memory_references: list[str] | None = None
    qualifying_log: bool | None = None
    log_case: str | None = None


class ToolCallFailedEvent(BaseModel):
    type: Literal["tool_call_failed"]
    tool_name: str
    target_resource: str | None = None
    command: str | None = None
    operation: str | None = None
    error_code: str | None = None
    memory_type: str | None = None
    provenance_trust: str | None = None
    source_artifact_id: str | None = None
    source_artifact_type: str | None = None
    invoice_id: str | None = None
    vendor_name: str | None = None
    vendor_id: str | None = None
    amount: float | None = None
    account_number: str | None = None
    retrieved_memory_references: list[str] | None = None
    qualifying_log: bool | None = None
    log_case: str | None = None


RuntimeStreamEventType = (
    TurnStartedEvent | TextChunkEvent | TurnCompletedEvent | TurnFailedEvent
)

RuntimeStreamEvent = Annotated[
    TurnStartedEvent
    | TextChunkEvent
    | TurnCompletedEvent
    | TurnFailedEvent
    | AttackEmailSentEvent
    | MaliciousEmailReadEvent
    | TokenDisclosureAttemptedEvent
    | TokenDisclosedEvent
    | TryAttackConsoleHintEvent
    | ToolCallRequestedEvent
    | ToolCallSucceededEvent
    | ToolCallFailedEvent,
    Field(discriminator="type"),
]


class EmailArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email_from: str = Field(min_length=1, max_length=64)
    email_subject: str = Field(min_length=1, max_length=64)
    email_body: str = Field(min_length=1, max_length=256)
    email_preview: str | None = None
    email_id: str | None = None
    malicious: bool | None = None
    urgency_marker: bool | None = None
    source: Literal["learner"] = "learner"

    @field_validator(
        "email_from", "email_subject", "email_body", "email_id", mode="before"
    )
    @classmethod
    def _strip_strings(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v


class ExplanationArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    explanation: str = Field(min_length=20, max_length=2048)
    source: Literal["learner"] = "learner"

    @field_validator("explanation", mode="before")
    @classmethod
    def _strip_strings(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v


class ApiError(BaseModel):
    code: str
    message: str
    retryable: bool
    details: dict[str, object] | None


class ApiErrorEnvelope(BaseModel):
    error: ApiError


class SessionCompletedEventPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    outcome: CompletionOutcome
    completion_reason_code: str | None = None
    trigger_event_index: int | None = None
    occurred_at: datetime
    idempotency_key: str = Field(min_length=1)


class SessionFeedbackCreatedEventPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    feedback_key: str = Field(min_length=1)
    reason_code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: FeedbackSeverity
    trigger_event_index: int | None = None
    created_at: datetime
    idempotency_key: str = Field(min_length=1)


class SessionCompletedOutboxEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: SessionCompletedEventName = "session.completed.v1"
    aggregate_id: UUID
    payload: SessionCompletedEventPayload


class SessionFeedbackCreatedOutboxEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: SessionFeedbackCreatedEventName = "session.feedback.created.v1"
    aggregate_id: UUID
    payload: SessionFeedbackCreatedEventPayload


OutboxEvent = Annotated[
    SessionCompletedOutboxEvent | SessionFeedbackCreatedOutboxEvent,
    Field(discriminator="event_type"),
]

OutboxEventType = OutboxEventName


class SessionEvaluateRequestedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lab_id: UUID
    lab_version_id: UUID
    lab_difficulty: str = "medium"
    evaluator_version: int
    start_event_index: int
    end_event_index: int


EvaluatorFeedbackStatusType = Literal[
    "learned", "progress", "no_progress", "session_terminal"
]
TraceEvidenceType = Literal[
    "exploit_step",
    "exploit_outcome",
    "system_context",
    "coaching_feedback",
    "noise",
]
TraceEvidencePriority = Literal["high", "medium", "low"]


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
    family: TraceFamily
    event_type: str
    source: str
    occurred_at: datetime
    payload: dict[str, Any]
    report_selectable: bool = False
    evidence_type: TraceEvidenceType = "noise"
    objective_keys: list[str] = Field(default_factory=list)
    why_it_matters: str | None = None
    default_priority: TraceEvidencePriority = "low"


class GetSessionTraceResponse(BaseModel):
    events: tuple[SessionTraceEvent, ...]
    next_cursor: str | None = None


class ReportEvidenceItem(BaseModel):
    event_id: UUID
    position: int
    title: str
    description: str | None = None
    occurred_at: datetime
    evidence_type: TraceEvidenceType
    objective_keys: tuple[str, ...] = ()
    why_it_matters: str | None = None
    default_priority: TraceEvidencePriority
    student_note: str | None = None


class GetSessionReportEvidenceResponse(BaseModel):
    items: tuple[ReportEvidenceItem, ...]


class PutSessionReportEvidenceRequest(BaseModel):
    items: tuple[ReportEvidenceItem, ...]


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
    severity: FeedbackSeverity
    trigger_event_index: int | None
    created_at: datetime
    seen_at: datetime | None


class SessionRuntimeFileResponse(BaseModel):
    path: str
    content: str
    updated_at: datetime


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
    completion_status: SessionCompletionStatus = "in_progress"
    completed_at: datetime | None = None
    completion_reason_code: str | None = None
    provisioning_stalled: bool = False
    provisioning_stall_reason_code: str | None = None
    progress_chips: list[SessionProgressChipResponse] = Field(default_factory=list)
    hints: list[SessionHintResponse] = Field(default_factory=list)
    unread_hint_count: int = 0
    feedback_items: list[SessionFeedbackResponse] = Field(default_factory=list)
    feedback: list[SessionFeedbackResponse] = Field(default_factory=list)
    unread_feedback_count: int = 0
    runtime_files: list[SessionRuntimeFileResponse] = Field(default_factory=list)


class GetSessionMetadataResponse(BaseModel):
    session: SessionMetadataResponse
