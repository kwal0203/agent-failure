from uuid import UUID
from typing import Mapping
from apps.control_plane.src.domain.session_lifecycle.state_machine import (
    Trigger,
    TRANSITIONS,
)
from datetime import datetime, timezone

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
        ts = datetime.now(timezone.utc)

        existing = uow.idempotency.get(
            operation="transition_session", key=idempotency_key
        )
        if existing is not None:
            return existing

        # Load session
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

        # Insert transition event
        transition_result = uow.sessions.insert_transition_event(
            session_id=session_id,
            prev_state=current_state,
            next_state=next_state,
            trigger=trigger,
            actor=actor,
            metadata=metadata,
            idempotency_key=idempotency_key,
        )

        # Update session state fields
        uow.sessions.update_state(
            session_id=session_id,
            from_state=current_state,
            to_state=next_state,
            actor=actor,
            reason=None,
        )

        # Enqueue transition to outbox
        uow.outbox.enqueue_for_transition(
            session_id=session_id,
            prev_state=current_state,
            next_state=next_state,
            trigger=trigger,
            metadata=metadata,
            transition_id=transition_result.transition_id,
        )

        if next_state in {"COMPLETED", "FAILED", "EXPIRED", "CANCELLED"}:
            uow.outbox.enqueue_for_cleanup(
                session_id=session_id,
                runtime_id=session.runtime_id,
                terminal_state=next_state,
                reason_code=None,
                requested_at=ts,
            )

        uow.idempotency.save(
            operation="transition_session",
            key=idempotency_key,
            result=transition_result,
        )
        return transition_result
