from pydantic import BaseModel, field_validator
from uuid import UUID


class ProvisioningPayload(BaseModel):
    lab_id: UUID
    lab_version_id: UUID
    lab_difficulty: str = "medium"

    @field_validator("lab_difficulty")
    @classmethod
    def normalize_difficulty(cls, v: str) -> str:
        value = v.strip().lower()
        if value not in {"easy", "medium"}:
            raise ValueError("invalid lab_difficulty")
        return value
