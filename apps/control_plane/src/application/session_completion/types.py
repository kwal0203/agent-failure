from typing import Literal, TypeAlias


CompletionStatus: TypeAlias = Literal[
    "in_progress", "completed_success", "completed_failure"
]

COMPLETION_STATUS_IN_PROGRESS: CompletionStatus = "in_progress"
COMPLETION_STATUS_COMPLETED_SUCCESS: CompletionStatus = "completed_success"
COMPLETION_STATUS_COMPLETED_FAILURE: CompletionStatus = "completed_failure"

TERMINAL_COMPLETION_STATUSES: tuple[CompletionStatus, ...] = (
    COMPLETION_STATUS_COMPLETED_SUCCESS,
    COMPLETION_STATUS_COMPLETED_FAILURE,
)
