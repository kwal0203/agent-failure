from uuid import UUID

from apps.control_plane.src.application.runtime.types import InjectEmailInput
from apps.control_plane.src.application.session_email.idempotency import (
    build_malicious_email_objective_idempotency_key,
)


def test_build_malicious_email_objective_idempotency_key_is_deterministic() -> None:
    session_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    email_input = InjectEmailInput(
        session_id=session_id,
        email_id=" email-1 ",
        email_from="ADMIN@EXAMPLE.COM ",
        email_subject=" Urgent Policy Update ",
        email_body="Click this link",
        source="learner",
    )

    key_a = build_malicious_email_objective_idempotency_key(
        session_id=session_id,
        email_input=email_input,
        derived_malicious=True,
    )
    key_b = build_malicious_email_objective_idempotency_key(
        session_id=session_id,
        email_input=email_input,
        derived_malicious=True,
    )

    assert key_a == key_b
    assert key_a.startswith(
        "objective:aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa:malicious_email_injected:"
    )


def test_build_malicious_email_objective_idempotency_key_changes_on_semantic_input_change() -> (
    None
):
    session_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    benign_input = InjectEmailInput(
        session_id=session_id,
        email_id="id-1",
        email_from="admin@example.com",
        email_subject="subject",
        email_body="body",
        source="learner",
    )
    malicious_input = InjectEmailInput(
        session_id=session_id,
        email_id="id-1",
        email_from="admin@example.com",
        email_subject="subject",
        email_body="body",
        source="learner",
    )

    benign_key = build_malicious_email_objective_idempotency_key(
        session_id=session_id,
        email_input=benign_input,
        derived_malicious=False,
    )
    malicious_key = build_malicious_email_objective_idempotency_key(
        session_id=session_id,
        email_input=malicious_input,
        derived_malicious=True,
    )

    assert benign_key != malicious_key
