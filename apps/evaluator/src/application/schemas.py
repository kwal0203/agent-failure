from pydantic import BaseModel, ConfigDict, Field


class OpenRouterExplanationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confidence: float = Field(ge=0.0, le=1.0)
    mentions_trust_boundary: bool = False
    mentions_rule_conflict: bool = False
    mentions_mitigation: bool = False
    mentions_root_cause: bool = False
    identified_agent_trusts_external_content: bool = False
    identified_rule_priority_clash: bool = False
