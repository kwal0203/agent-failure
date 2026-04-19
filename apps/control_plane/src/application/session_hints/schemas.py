from datetime import datetime
import re
from uuid import UUID

from pydantic import BaseModel, field_validator

HINT_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class HintUnlockedEventPayload(BaseModel):
    session_id: UUID
    hint_key: str
    text: str
    sort_order: int
    unlocked_at: datetime
    idempotency_key: str

    @field_validator("hint_key")
    @classmethod
    def _normalize_hint_key(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("hint_key must not be empty")
        if not HINT_KEY_PATTERN.match(normalized):
            raise ValueError(
                "hint_key must be lowercase snake_case (letters, numbers, underscores)"
            )
        return normalized

    @field_validator("text", "idempotency_key")
    @classmethod
    def _non_empty_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized

    @field_validator("sort_order")
    @classmethod
    def _non_negative_sort_order(cls, value: int) -> int:
        if value < 0:
            raise ValueError("sort_order must be >= 0")
        return value
