from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class PrincipalContext:
    user_id: UUID
    role: str


@dataclass(frozen=True)
class LabRuntimeBinding:
    lab_slug: str
    lab_version: str
