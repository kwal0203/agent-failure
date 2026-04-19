from typing import cast

from .types import HintStatus, ProgressStatus


def parse_progress_status(value: str) -> ProgressStatus:
    if value == "pending" or value == "complete":
        return cast(ProgressStatus, value)
    raise ValueError(f"Invalid progress status in DB: {value}")


def parse_hint_status(value: str) -> HintStatus:
    if value == "pending" or value == "unlocked":
        return cast(HintStatus, value)
    raise ValueError(f"Invalid hint status in DB: {value}")
