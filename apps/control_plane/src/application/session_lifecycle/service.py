from uuid import UUID
from typing import Mapping
from apps.control_plane.src.domain.session_lifecycle.state_machine import (
    Trigger,
    TRANSITIONS,
)
from .ports import UnitOfWork
from .schemas import TransitionResult
from .validators import validate_transition
from .errors import SessionNotFound, InvalidTransition


def transition_session(
    session_id: UUID,
    trigger: Trigger,
    actor: str,
    metadata: Mapping[str, object],
    idempotency_key: str,
    uow: UnitOfWork,
) -> TransitionResult:
    with uow.transaction():
        existing = uow.idempotency.get(
            operation="transition_session", key=idempotency_key
        )
        if existing is not None:
            return existing

        session = uow.sessions.get_for_update(session_id=session_id)
        if session is None:
            raise SessionNotFound(session_id=session_id)

        current_state = session.state

        rule = TRANSITIONS.get(current_state, {}).get(trigger)
        if rule is None:
            raise InvalidTransition(current_state=current_state, trigger=trigger)

        next_state = rule.next_state

        # Validate guards/invariants: authz, resume policy, terminal-state checks, etc.
        validate_transition(
            session=session,
            trigger=trigger,
            actor=actor,
            metadata=metadata,
            next_state=next_state,
        )

        uow.sessions.update_state(
            session_id=session_id,
            from_state=current_state,
            to_state=next_state,
            actor=actor,
            reason=None,
        )

        transition_result = uow.sessions.insert_transition_event(
            session_id=session_id,
            prev_state=current_state,
            next_state=next_state,
            trigger=trigger,
            actor=actor,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )

        uow.outbox.enqueue_for_transition(
            session_id=session_id,
            prev_state=current_state,
            next_state=next_state,
            trigger=trigger,
            metadata=metadata,
            transition_id=transition_result.transition_id,
        )

        uow.idempotency.save(
            operation="transition_session",
            key=idempotency_key,
            result=transition_result,
        )
        return transition_result
