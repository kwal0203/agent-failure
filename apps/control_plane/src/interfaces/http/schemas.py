from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class ApiError(BaseModel):
    code: str
    message: str
    retryable: bool
    details: dict[str, object] | None


class ApiErrorEnvelope(BaseModel):
    error: ApiError


class SessionMetadataResponse(BaseModel):
    id: UUID
    lab_id: UUID | None
    lab_version_id: UUID | None
    state: str
    runtime_substate: str | None
    resume_mode: str
    interactive: bool
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None


class GetSessionMetadataResponse(BaseModel):
    session: SessionMetadataResponse


class SessionResponse(BaseModel):
    id: UUID
    lab_id: UUID
    # TODO: Make lab_version_id non-null once lab version binding is implemented in create flow.
    lab_version_id: UUID | None
    state: str
    resume_mode: str
    created_at: datetime


class CreateSessionResponse(BaseModel):
    session: SessionResponse


class CreateSessionRequest(BaseModel):
    lab_id: UUID


class LabCapabilitiesResponse(BaseModel):
    supports_resume: bool
    supports_uploads: bool


class LabCatalogItemResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    summary: str
    capabilities: LabCapabilitiesResponse


class GetLabsResponse(BaseModel):
    labs: list[LabCatalogItemResponse]
