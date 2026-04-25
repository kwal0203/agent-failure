from dataclasses import dataclass


@dataclass(frozen=True)
class AuthorityBulletinClassificationInput:
    prompt_content: str
    expected_signer: str


@dataclass(frozen=True)
class AuthorityBulletinClassificationResult:
    is_authority_bulletin: bool
    signer_name: str | None = None
    confidence: float | None = None
    reason: str | None = None
    provider: str | None = None
    model: str | None = None
