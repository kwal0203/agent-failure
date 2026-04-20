from uuid import UUID


def build_hint_unlock_idempotency_key(*, session_id: UUID, hint_key: str) -> str:
    normalized_hint_key = hint_key.strip().lower()
    return f"hint_unlock:{session_id}:{normalized_hint_key}"
