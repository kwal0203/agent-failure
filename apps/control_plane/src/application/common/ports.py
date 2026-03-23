from typing import Generic, TypeVar, Protocol
from uuid import UUID

from .types import LabRuntimeBinding, GetLabCatalogRow


T = TypeVar("T")


class IdempotencyStore(Protocol, Generic[T]):
    def get(self, operation: str, key: str) -> T | None: ...
    def save(self, operation: str, key: str, result: T) -> None: ...


class LabRepository(Protocol):
    def get_lab_catalog(self) -> list[GetLabCatalogRow]: ...
    def validate_lab(self, lab_id: UUID) -> bool: ...
    def get_runtime_binding(
        self, lab_id: UUID, lab_version_id: UUID
    ) -> LabRuntimeBinding: ...
