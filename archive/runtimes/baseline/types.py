from dataclasses import dataclass
from uuid import UUID

from apps.contracts.src.schemas import RuntimeStreamEvent


@dataclass(frozen=True)
class RuntimeTurnInput:
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    turn_id: UUID
    prompt: str
    idempotency_key: str | None = None
    authority_bulletin_passed: bool | None = None
    authority_bulletin_signer: str | None = None
    authority_bulletin_destructive_db_delete: bool | None = None


@dataclass(frozen=True)
class TextItem:
    content: str


@dataclass(frozen=True)
class EventItem:
    event: RuntimeStreamEvent


RuntimeExecutorItem = TextItem | EventItem
