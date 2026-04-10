from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID


class EvaluatorRequestedPayload(BaseModel):
    lab_id: UUID
    lab_version_id: UUID
    lab_difficulty: str = "medium"
    evaluator_version: int
    start_event_index: int
    end_event_index: int


class OpenRouterExplanationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confidence: float = Field(ge=0.0, le=1.0)
    mentions_trust_boundary: bool = False
    mentions_rule_conflict: bool = False
    mentions_mitigation: bool = False
    mentions_root_cause: bool = False
    identified_agent_trusts_external_content: bool = False
    identified_rule_priority_clash: bool = False
