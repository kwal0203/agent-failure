from uuid import UUID
from apps.control_plane.src.domain.session_lifecycle.state_machine import (
    SessionState,
    Trigger,
)


class SessionNotFound(Exception):
    def __init__(self, session_id: UUID) -> None:
        super().__init__(f"Session not found: {session_id}")
        self.session_id = session_id


class InvalidTransition(Exception):
    def __init__(self, current_state: SessionState, trigger: Trigger) -> None:
        super().__init__(f"Invalid transition {current_state} + {trigger}")
        self.current_state = current_state
        self.trigger = trigger


class TransitionValidationError(Exception):
    def __init__(self, msg: str) -> None:
        super().__init__(f"{msg}")
        self.msg = msg
