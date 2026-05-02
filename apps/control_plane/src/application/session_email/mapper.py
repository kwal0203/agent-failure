from apps.control_plane.src.application.runtime.types import InjectEmailInput
from apps.control_plane.src.application.session_email.payloads import (
    AttackEmailSentPayload,
)


def map_attack_email_sent_payload(
    *,
    email_input: InjectEmailInput,
    derived_malicious: bool,
    classifier_provider: str | None,
    classifier_model: str | None,
    classifier_confidence: float | None,
    urgency_marker: bool | None,
) -> AttackEmailSentPayload:
    email_id = email_input.email_id or ""
    return {
        "type": "attack_email_sent",
        "email_id": email_id,
        "email_from": email_input.email_from,
        "subject": email_input.email_subject,
        "malicious_marker": derived_malicious,
        "urgency_marker": urgency_marker,
        "classifier_provider": classifier_provider,
        "classifier_model": classifier_model,
        "classifier_confidence": classifier_confidence,
    }
