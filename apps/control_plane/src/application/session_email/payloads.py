from typing import TypedDict


class AttackEmailSentPayload(TypedDict):
    type: str
    email_id: str
    email_from: str
    subject: str
    malicious_marker: bool
    urgency_marker: bool | None
    classifier_provider: str | None
    classifier_model: str | None
    classifier_confidence: float | None
