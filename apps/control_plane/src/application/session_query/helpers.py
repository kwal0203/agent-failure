from typing import cast

from apps.control_plane.src.application.session_completion.types import (
    COMPLETION_STATUS_COMPLETED_FAILURE,
    COMPLETION_STATUS_COMPLETED_SUCCESS,
    COMPLETION_STATUS_IN_PROGRESS,
)

from .types import CompletionStatus, FeedbackSeverity, HintStatus, ProgressStatus


def parse_progress_status(value: str) -> ProgressStatus:
    if value == "pending" or value == "complete":
        return cast(ProgressStatus, value)
    raise ValueError(f"Invalid progress status in DB: {value}")


def parse_hint_status(value: str) -> HintStatus:
    if value == "pending" or value == "unlocked":
        return cast(HintStatus, value)
    raise ValueError(f"Invalid hint status in DB: {value}")


def parse_completion_status(value: str) -> CompletionStatus:
    if (
        value == COMPLETION_STATUS_IN_PROGRESS
        or value == COMPLETION_STATUS_COMPLETED_SUCCESS
        or value == COMPLETION_STATUS_COMPLETED_FAILURE
    ):
        return cast(CompletionStatus, value)
    raise ValueError(f"Invalid completion status in DB: {value}")


def parse_feedback_severity(value: str) -> FeedbackSeverity:
    if value == "info" or value == "warning" or value == "error":
        return cast(FeedbackSeverity, value)
    raise ValueError(f"Invalid feedback severity in DB: {value}")
