from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
from typing import cast, TypeAlias, Literal

from apps.control_plane.src.application.session_completion.types import CompletionStatus


ProgressStatus: TypeAlias = Literal["pending", "complete"]
HintStatus: TypeAlias = Literal["pending", "unlocked"]
FeedbackSeverity: TypeAlias = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class SessionObjectiveRow:
    objective_key: str
    label: str
    status: ProgressStatus
    completed_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True)
class SessionHintRow:
    hint_key: str
    text: str
    sort_order: int
    status: HintStatus
    unlock_at: datetime
    unlocked_at: datetime | None
    seen_at: datetime | None


@dataclass(frozen=True)
class SessionFeedbackRow:
    id: UUID
    feedback_key: str
    reason_code: str
    message: str
    severity: FeedbackSeverity
    trigger_event_index: int | None
    created_at: datetime
    seen_at: datetime | None


@dataclass(frozen=True)
class SessionMetadataRow:
    id: UUID
    lab_id: UUID | None
    lab_version_id: UUID | None
    owner_user_id: UUID
    state: str
    runtime_substate: str | None
    resume_mode: str
    last_transition_reason: str | None
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None
    completion_status: CompletionStatus = "in_progress"
    completed_at: datetime | None = None
    completion_reason_code: str | None = None
    lab_difficulty: str = "medium"


@dataclass(frozen=True)
class SessionObjectiveDTO:
    objective_key: str
    label: str
    status: ProgressStatus
    completed_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True)
class SessionHintDTO:
    hint_key: str
    text: str
    sort_order: int
    status: HintStatus
    unlock_at: datetime
    unlocked_at: datetime | None
    seen_at: datetime | None


@dataclass(frozen=True)
class SessionFeedbackDTO:
    id: UUID
    feedback_key: str
    reason_code: str
    message: str
    severity: FeedbackSeverity
    trigger_event_index: int | None
    created_at: datetime
    seen_at: datetime | None


@dataclass(frozen=True)
class SessionMetadataDTO:
    id: UUID
    lab_id: UUID | None
    lab_version_id: UUID | None
    owner_user_id: UUID
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
    lab_difficulty: str = "medium"
    progress_chips: list[SessionObjectiveDTO] = field(
        default_factory=lambda: cast(list[SessionObjectiveDTO], [])
    )
    hints: list[SessionHintDTO] = field(
        default_factory=lambda: cast(list[SessionHintDTO], [])
    )
    unread_hint_count: int = 0
    feedback_items: list[SessionFeedbackDTO] = field(
        default_factory=lambda: cast(list[SessionFeedbackDTO], [])
    )
    # Backward-compat alias; new clients should use feedback_items.
    feedback: list[SessionFeedbackDTO] = field(
        default_factory=lambda: cast(list[SessionFeedbackDTO], [])
    )
    unread_feedback_count: int = 0


@dataclass(frozen=True)
class SessionMetadataBundleRow:
    metadata: SessionMetadataRow
    objectives: list[SessionObjectiveRow]
    hints: list[SessionHintRow]
    feedback: list[SessionFeedbackRow]


@dataclass(frozen=True)
class SessionSummaryRow:
    session_id: UUID
    lab_id: UUID
    created_at: datetime
    state: str
    completion_status: CompletionStatus


@dataclass(frozen=True)
class SessionSummaryDTO:
    session_id: UUID
    lab_id: UUID
    created_at: datetime
    state: str
    completion_status: CompletionStatus
