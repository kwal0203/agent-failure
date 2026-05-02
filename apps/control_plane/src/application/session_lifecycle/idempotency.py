"""Idempotency key builders for session lifecycle transitions."""

from uuid import UUID


def build_stop_session_transition_idempotency_key(
    *, session_id: UUID, requester_user_id: UUID
) -> str:
    return f"stop-session:{session_id}:{requester_user_id}"
