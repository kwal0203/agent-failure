from datetime import datetime
import re
from uuid import UUID

from pydantic import BaseModel, field_validator

OBJECTIVE_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class ObjectiveCompletedEventPayload(BaseModel):
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    objective_key: str
    reason_code: str
    trigger_event_index: int
    occurred_at: datetime
    idempotency_key: str
    source: str = "evaluator"
    evaluator_version: int | None = None

    @field_validator("objective_key")
    @classmethod
    def _normalize_objective_key(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("objective_key must not be empty")
        if not OBJECTIVE_KEY_PATTERN.match(normalized):
            raise ValueError(
                "objective_key must be lowercase snake_case "
                "(letters, numbers, underscores)"
            )
        return normalized

    @field_validator("reason_code", "idempotency_key")
    @classmethod
    def _non_empty_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("value must not be empty")
        return normalized
