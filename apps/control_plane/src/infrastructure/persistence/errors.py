from uuid import UUID
from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState


class StateMismatch(Exception):
    def __init__(self, session_id: UUID, from_state: SessionState) -> None:
        super().__init__(f"Session {session_id} was not in expected state {from_state}")
        self.session_id = session_id
        self.from_state = from_state
