from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetLabsCapabilities:
    supports_resume: bool
    supports_uploads: bool


@dataclass(frozen=True)
class GetLabsItemResult:
    lab_id: UUID
    slug: str
    name: str
    summary: str
    capabilities: GetLabsCapabilities


@dataclass(frozen=True)
class GetLabsForPrincipalResult:
    labs: list[GetLabsItemResult]
