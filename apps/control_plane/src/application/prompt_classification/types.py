from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class AuthorityBulletinClassificationInput:
    prompt_content: str
    expected_signer: str


@dataclass(frozen=True)
class AuthorityBulletinClassificationResult:
    is_authority_bulletin: bool
    signer_name: str | None = None
    runbook_action_type: Literal["prod_db_delete", "other"] | None = None
    destructive_db_delete: bool | None = None
    confidence: float | None = None
    reason: str | None = None
    provider: str | None = None
    model: str | None = None
