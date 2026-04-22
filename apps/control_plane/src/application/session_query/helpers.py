from typing import cast

from .types import CompletionStatus, HintStatus, ProgressStatus


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
        value == "in_progress"
        or value == "completed_success"
        or value == "completed_failure"
    ):
        return cast(CompletionStatus, value)
    raise ValueError(f"Invalid completion status in DB: {value}")
