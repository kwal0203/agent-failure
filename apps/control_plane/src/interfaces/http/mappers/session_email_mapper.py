import hashlib
from uuid import UUID

from apps.control_plane.src.application.runtime.types import InjectEmailInput


def map_attack_email_sent_payload(
    *,
    email_input: InjectEmailInput,
    derived_malicious: bool,
    classifier_provider: str | None,
    classifier_model: str | None,
    classifier_confidence: float | None,
    urgency_marker: bool | None,
) -> dict[str, object]:
    return {
        "type": "attack_email_sent",
        "email_id": email_input.email_id,
        "email_from": email_input.email_from,
        "subject": email_input.email_subject,
        "malicious_marker": derived_malicious,
        "urgency_marker": urgency_marker,
        "classifier_provider": classifier_provider,
        "classifier_model": classifier_model,
        "classifier_confidence": classifier_confidence,
    }


def build_malicious_email_objective_idempotency_key(
    *,
    session_id: UUID,
    email_input: InjectEmailInput,
    derived_malicious: bool,
) -> str:
    fingerprint = hashlib.sha256(
        "|".join(
            [
                str(session_id),
                email_input.email_from.strip().lower(),
                email_input.email_subject.strip(),
                email_input.email_body.strip(),
                str(derived_malicious),
                (email_input.source or "learner").strip().lower(),
                (email_input.email_id or "").strip(),
            ]
        ).encode("utf-8")
    ).hexdigest()
    return f"objective:{session_id}:malicious_email_injected:{fingerprint}"
