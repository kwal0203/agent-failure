from pydantic import BaseModel
from uuid import UUID


class ProvisioningPayload(BaseModel):
    lab_id: UUID
    lab_version_id: UUID
