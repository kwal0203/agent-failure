from typing import cast

from .types import ProgressStatus


def parse_progress_status(value: str) -> ProgressStatus:
    if value == "pending" or value == "complete":
        return cast(ProgressStatus, value)
    raise ValueError(f"Invalid progress status in DB: {value}")
