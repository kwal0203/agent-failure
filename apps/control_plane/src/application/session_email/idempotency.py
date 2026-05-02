"""Idempotency key builders for session email workflows."""

import hashlib
from uuid import UUID

from apps.control_plane.src.application.runtime.types import InjectEmailInput


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
