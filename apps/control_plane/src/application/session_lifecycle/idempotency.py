from typing import Protocol
from uuid import UUID
from .schemas import TransitionResult


class IdempotencyStore(Protocol):
    def get(self, key: UUID) -> TransitionResult: ...

    def save(self, key: UUID, result: object) -> None: ...
