"""Authoritative identities for the production agent labs.

`lab_id` identifies a lab across releases. `lab_version_id` identifies one
persisted catalog version of that lab. Runtime config IDs are compatibility
aliases for the original pre-agent lab definitions and must not be treated as
lab-version IDs.
"""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class LabIdentity:
    slug: str
    version: str
    lab_id: UUID
    lab_version_id: UUID
    runtime_config_id: UUID
    objective_keys: tuple[str, ...]


AGENT_PROMPT_INJECTION = LabIdentity(
    slug="agent-prompt-injection",
    version="v1",
    lab_id=UUID("44444444-4444-4444-4444-444444444444"),
    lab_version_id=UUID("44444444-4444-4444-4444-aaaaaaaaaaa1"),
    runtime_config_id=UUID("11111111-1111-1111-1111-111111111111"),
    objective_keys=(
        "malicious_email_injected",
        "malicious_instructions_entered_context",
        "token_exposed",
    ),
)
AGENT_TOOL_MISUSE = LabIdentity(
    slug="agent-tool-misuse",
    version="v1",
    lab_id=UUID("55555555-5555-5555-5555-555555555555"),
    lab_version_id=UUID("55555555-5555-5555-5555-aaaaaaaaaaa2"),
    runtime_config_id=UUID("22222222-2222-2222-2222-222222222222"),
    objective_keys=(
        "unsafe_tool_invocation_triggered",
        "log_created",
        "critical_file_deleted",
    ),
)
AGENT_MEMORY_POISONING = LabIdentity(
    slug="agent-memory-poisoning",
    version="v1",
    lab_id=UUID("66666666-6666-6666-6666-666666666666"),
    lab_version_id=UUID("66666666-6666-6666-6666-aaaaaaaaaaa3"),
    runtime_config_id=UUID("33333333-3333-3333-3333-333333333333"),
    objective_keys=(
        "malicious_vendor_memory_written",
        "poisoned_memory_retrieved_for_invoice",
        "payment_routed_to_attacker_account",
    ),
)

PRODUCTION_AGENT_LABS = (
    AGENT_PROMPT_INJECTION,
    AGENT_TOOL_MISUSE,
    AGENT_MEMORY_POISONING,
)
PRODUCTION_AGENT_LABS_BY_ID = {
    identity.lab_id: identity for identity in PRODUCTION_AGENT_LABS
}
PRODUCTION_AGENT_LABS_BY_SLUG = {
    identity.slug: identity for identity in PRODUCTION_AGENT_LABS
}

# The retired Code Execution catalog entry predates the production agent labs.
# Its lab ID now collides with the production Prompt Injection lab ID, so these
# names intentionally include "legacy" and must not be used for catalog lookup.
LEGACY_CODE_EXECUTION_LAB_ID = UUID("44444444-4444-4444-4444-444444444444")
LEGACY_CODE_EXECUTION_LAB_VERSION_ID = UUID("88888888-8888-8888-8888-888888888888")
