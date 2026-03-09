from apps.control_plane.src.domain.session_lifecycle.state_machine import (
    SessionState,
    Trigger,
)
from typing import Mapping
from .ports import SessionRow
from .errors import TransitionValidationError


def validate_transition(
    session: SessionRow,
    trigger: Trigger,
    actor: str,
    metadata: Mapping[str, object],
    next_state: SessionState,
) -> None:
    if not actor.strip():
        raise TransitionValidationError(msg="Actor is required.")

    if trigger == trigger.ADMIN_CANCELLED and actor != "admin":
        raise TransitionValidationError(msg="Only admin can cancel jobs.")

    if next_state == SessionState.COMPLETED and "outcome" not in metadata:
        raise TransitionValidationError(
            msg="Successful state transition requires an outcome."
        )

    if next_state == SessionState.FAILED and "reason_code" not in metadata:
        raise TransitionValidationError(
            msg="Unsuccessful state transition requires a reason."
        )
