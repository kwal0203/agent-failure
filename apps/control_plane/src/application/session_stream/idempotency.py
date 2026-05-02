"""Idempotency key builders for websocket turn streaming."""

from uuid import UUID


def build_turn_idempotency_key(*, session_id: UUID, turn_id: UUID) -> str:
    return f"turn:{session_id}:{turn_id}"
