from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class EmailClassificationInput:
    email_from: str
    email_subject: str
    email_body: str


@dataclass(frozen=True)
class EmailClassificationResult:
    malicious: bool
    confidence: float | None = None
    reason: str | None = None
    provider: str | None = None
    model: str | None = None
    verdict: Literal["malicious", "benign"] | None = None
