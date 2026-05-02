"""Idempotency key builders for orchestrator workflows."""

from uuid import UUID


def build_provision_request_idempotency_key(
    *, session_id: UUID, outbox_event_id: UUID
) -> str:
    return f"provision:{session_id}:{outbox_event_id}"


def build_provisioning_succeeded_transition_idempotency_key(
    *, session_id: UUID, outbox_event_id: UUID
) -> str:
    return f"provisioning:{session_id}:{outbox_event_id}:succeeded"


def build_provisioning_failed_transition_idempotency_key(
    *, session_id: UUID, outbox_event_id: UUID
) -> str:
    return f"provisioning:{session_id}:{outbox_event_id}:failed"


def build_reconcile_missing_runtime_transition_idempotency_key(
    *, session_id: UUID, state: str
) -> str:
    return f"reconcile:{session_id}:missing-runtime:{state.strip().upper()}"


def build_reconcile_failed_runtime_transition_idempotency_key(
    *, session_id: UUID, state: str
) -> str:
    return f"reconcile:{session_id}:failed-runtime:{state.strip().upper()}"


def build_expired_provisioning_transition_idempotency_key(
    *, session_id: UUID, state: str
) -> str:
    return f"expiry:{session_id}:expired-provisioning:{state.strip().upper()}"


def build_expired_session_transition_idempotency_key(
    *, session_id: UUID, state: str
) -> str:
    return f"expiry:{session_id}:expired-session:{state.strip().upper()}"
