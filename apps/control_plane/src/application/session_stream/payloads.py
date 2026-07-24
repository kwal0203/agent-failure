from typing import TypedDict


class LearnerPromptSubmittedPayload(TypedDict, total=False):
    content: str
    role: str
    channel: str
    message_type: str
    authority_bulletin_passed: bool
    authority_bulletin_runbook_action_type: str | None
    authority_bulletin_destructive_db_delete: bool | None


class ModelTurnStartedPayload(TypedDict):
    provider: str
    message_type: str
    prompt_chars: int


class ModelTurnFailedPayload(TypedDict):
    provider: str
    error_code: str
    retryable: bool
    phase: str
    duration_ms: int
    chunks_emitted: int


class ModelTurnCompletedPayload(TypedDict):
    status: str
    chunks_emitted: int
    duration_ms: int
    first_chunk_emitted: bool
    content: str


class RuntimeEventPayload(TypedDict, total=False):
    type: str
    email_id: str
    recipient: str
    subject: str
    message: str
    tool_name: str
    target_resource: str
    command: str
    operation: str
    memory_type: str
    provenance_trust: str
    source_artifact_id: str
    source_artifact_type: str
    invoice_id: str
    vendor_name: str
    vendor_id: str
    amount: str
    account_number: str
    retrieved_memory_references: str
    qualifying_log: str
    log_case: str
    deleted: bool
    exists_after: bool
    authority_bulletin_passed: bool
    authority_bulletin_destructive_db_delete: bool
    authority_bulletin_runbook_action_type: str
    error_code: str
    malicious_marker: bool
    channel: str
    target: str
    token_kind: str
    signal_id: str
    section: str
    severity: str
    simulated: bool
