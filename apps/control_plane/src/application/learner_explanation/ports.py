from typing import Protocol
from uuid import UUID

from .types import LearnerExplanationInput, LearnerExplanationOutput


class LearnerExplanationPort(Protocol):
    def get_by_session_and_idempotency_key(
        self, *, session_id: UUID, idempotency_key: str
    ) -> LearnerExplanationOutput | None: ...

    def inject_learner_explanation(
        self, input: LearnerExplanationInput
    ) -> LearnerExplanationOutput: ...
