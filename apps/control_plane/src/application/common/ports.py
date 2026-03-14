from typing import Generic, TypeVar, Protocol


T = TypeVar("T")


class IdempotencyStore(Protocol, Generic[T]):
    def get(self, operation: str, key: str) -> T | None: ...
    def save(self, operation: str, key: str, result: T) -> None: ...
