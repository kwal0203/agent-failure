from dataclasses import dataclass


@dataclass(frozen=True)
class AdmissionDecision:
    allowed: bool
    code: str | None
    message: str | None
    retryable: bool
    details: dict[str, object] | None
