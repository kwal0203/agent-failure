from datetime import datetime
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class HintTemplate:
    hint_key: str
    text: str
    offset_seconds: int
    sort_order: int


@dataclass(frozen=True)
class DueSessionHint:
    session_id: UUID
    hint_key: str
    text: str
    sort_order: int
    unlock_at: datetime


@dataclass(frozen=True)
class SessionHintUnlockOnceResult:
    claimed_count: int
    succeeded_count: int
    skipped_count: int
