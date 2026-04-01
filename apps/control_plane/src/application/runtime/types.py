from dataclasses import dataclass
from uuid import UUID
from typing import Literal


@dataclass(frozen=True)
class RuntimeClientConfig:
    base_url: str
    timeout_seconds: float = 20.0
    auth_token: str | None = None


@dataclass(frozen=True)
class RunTurnInput:
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    turn_id: UUID
    prompt: str
    idempotency_key: str | None = None


@dataclass(frozen=True)
class RunTurnOutput:
    turn_id: UUID
    status: Literal["completed", "failed"]
    output_text: str
    chunks_emitted: int
    duration_ms: int
    model_provider: str | None = None
    model_name: str | None = None
