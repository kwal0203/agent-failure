from dataclasses import dataclass
from uuid import UUID
from typing import Literal


LabDifficulty = Literal["easy", "medium"]
ALLOWED_LAB_DIFFICULTIES: frozenset[str] = frozenset({"easy", "medium"})


@dataclass(frozen=True)
class PrincipalContext:
    user_id: UUID
    role: str
    email: str | None = None


@dataclass(frozen=True)
class LabRuntimeBinding:
    lab_slug: str
    lab_version: str


@dataclass(frozen=True)
class GetLabCatalogRow:
    lab_id: UUID
    slug: str
    name: str
    summary: str
    supports_resume: bool
    supports_uploads: bool
