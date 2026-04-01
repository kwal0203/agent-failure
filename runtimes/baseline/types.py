from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RuntimeTurnInput:
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    turn_id: UUID
    prompt: str
    idempotency_key: str | None = None
