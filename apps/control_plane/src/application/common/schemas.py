from pydantic import BaseModel, field_validator
from .types import LabDifficulty


class LabDifficultyParser(BaseModel):
    lab_difficulty: LabDifficulty

    @field_validator("lab_difficulty", mode="before")
    @classmethod
    def _strip_strings(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v
