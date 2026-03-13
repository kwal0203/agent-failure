from pydantic import BaseModel
from uuid import UUID
from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState


class TransitionResult(BaseModel):
    transition_id: UUID
    session_id: UUID
    prev_state: SessionState
    next_state: SessionState


class IdempotencyRecord(BaseModel):
    key: str
    result: TransitionResult | None = None
