from dataclasses import dataclass
from uuid import UUID
from typing import Literal, Mapping

Status = Literal["accepted", "ready", "failed"]


@dataclass(frozen=True)
class RuntimeProvisionRequest:
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    image_ref: str
    metadata: Mapping[str, object]


@dataclass(frozen=True)
class ProvisionResult:
    status: Status
    runtime_id: str | None = None
    reason_code: str | None = None
    details: dict[str, object] | None = None
