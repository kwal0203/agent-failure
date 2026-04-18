from uuid import UUID


def build_objective_event_idempotency_key(
    *,
    session_id: UUID,
    objective_key: str,
    trigger_event_index: int,
) -> str:
    normalized_objective_key = objective_key.strip().lower()
    return f"objective:{session_id}:{normalized_objective_key}:{trigger_event_index}"
