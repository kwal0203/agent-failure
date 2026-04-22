from uuid import UUID

from .types import CompletionOutcome


def build_session_completed_event_idempotency_key(
    *,
    session_id: UUID,
    outcome: CompletionOutcome,
    completion_reason_code: str | None,
    trigger_event_index: int | None,
) -> str:
    """
    Build a deterministic idempotency key for `session.completed.v1`.

    Canonical input tuple:
    - session_id
    - outcome
    - completion_reason_code (normalized: strip + lower; empty -> "none")
    - trigger_event_index (None -> "none")
    """

    normalized_reason = (completion_reason_code or "").strip().lower() or "none"
    normalized_trigger = (
        str(trigger_event_index) if trigger_event_index is not None else "none"
    )
    return (
        f"session_completed:{session_id}:{outcome}:"
        f"{normalized_reason}:{normalized_trigger}"
    )
