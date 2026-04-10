from dataclasses import dataclass
from uuid import UUID

from apps.control_plane.src.application.common.types import LabDifficulty


@dataclass(frozen=True)
class LearnerExplanationInput:
    explanation: str
    session_id: UUID
    lab_id: UUID
    lab_version_id: UUID
    lab_difficulty: LabDifficulty
    actor_user_id: UUID
    idempotency_key: str
    source: str = "learner"


@dataclass(frozen=True)
class LearnerExplanationOutput:
    session_id: UUID
    explanation_id: UUID
    accepted: bool = True
