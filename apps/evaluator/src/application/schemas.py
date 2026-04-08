from pydantic import BaseModel
from uuid import UUID


class EvaluatorRequestedPayload(BaseModel):
    lab_id: UUID
    lab_version_id: UUID
    lab_difficulty: str = "medium"
    evaluator_version: int
    start_event_index: int
    end_event_index: int
