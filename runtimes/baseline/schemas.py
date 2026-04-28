from pydantic import BaseModel
from uuid import UUID


class HealthStatus(BaseModel):
    status: str
    runtime: str | None = None


class InjectEmailResponse(BaseModel):
    session_id: UUID
    accepted: bool = True
    email_id: str | None = None
