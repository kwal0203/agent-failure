from apps.control_plane.src.application.session_create.schemas import (
    CreateSessionResult,
)
from apps.control_plane.src.application.session_create.ports import (
    CreateSessionRepository,
)

from apps.control_plane.src.application.session_lifecycle.ports import (
    SessionRepository,
    SessionRow,
)
from apps.control_plane.src.application.session_lifecycle.schemas import (
    TransitionResult,
)

from apps.control_plane.src.application.session_query.ports import (
    SessionMetadataRepository,
    SessionMetadataDTO,
)

from apps.control_plane.src.domain.session_lifecycle.state_machine import (
    SessionState,
    Trigger,
)

from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from datetime import datetime, timezone
from typing import Mapping, cast
from uuid import UUID, uuid4

from .models import SessionModel, SessionTransitionEventModel
from .errors import StateMismatch


class SQLAlchemySessionRepository(SessionRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_for_update(self, session_id: UUID) -> SessionRow | None:
        stmt = (
            select(SessionModel).where(SessionModel.id == session_id).with_for_update()
        )

        row = self._db.execute(stmt).scalar_one_or_none()
        if row is None:
            return None

        return SessionRow(id=row.id, state=SessionState(row.state))

    def update_state(
        self,
        session_id: UUID,
        from_state: SessionState,
        to_state: SessionState,
        actor: str,
        reason: str | None,
    ) -> None:
        stmt = (
            update(SessionModel)
            .where(
                SessionModel.id == session_id, SessionModel.state == from_state.value
            )
            .values(
                state=to_state.value,
                last_transition_actor=actor,
                last_transition_reason=reason,
            )
        )

        result = cast(CursorResult[object], self._db.execute(stmt))
        if result.rowcount != 1:
            raise StateMismatch(session_id=session_id, from_state=from_state)

    def insert_transition_event(
        self,
        session_id: UUID,
        prev_state: SessionState,
        next_state: SessionState,
        trigger: Trigger,
        actor: str,
        metadata: Mapping[str, object],
        idempotency_key: str,
    ) -> TransitionResult:
        transition_id = uuid4()

        event = SessionTransitionEventModel(
            id=transition_id,
            session_id=session_id,
            prev_state=prev_state.value,
            next_state=next_state.value,
            trigger=trigger.value,
            actor=actor,
            event_metadata=dict(metadata),
            idempotency_key=idempotency_key,
            created_at=datetime.now(timezone.utc),
        )

        self._db.add(event)
        # Ensure the transition event row exists before idempotency save
        # writes a FK reference to this transition_id in the same transaction.
        self._db.flush()

        return TransitionResult(
            transition_id=transition_id,
            session_id=session_id,
            prev_state=prev_state,
            next_state=next_state,
        )


class SQLAlchemySessionMetadataRepository(SessionMetadataRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_session_metadata(self, session_id: UUID) -> SessionMetadataDTO | None:
        stmt = select(SessionModel).where(SessionModel.id == session_id)
        result = self._db.execute(statement=stmt).scalar_one_or_none()
        if result is None:
            return None

        return SessionMetadataDTO(
            id=result.id,
            lab_id=result.lab_id,
            lab_version_id=result.lab_version_id,
            state=result.state,
            runtime_substate=result.runtime_substate,
            resume_mode=result.resume_mode,
            # TODO: Move interactive derivation to application/service mapping.
            interactive=result.state in {SessionState.ACTIVE, SessionState.IDLE},
            created_at=result.created_at,
            started_at=result.started_at,
            ended_at=result.ended_at,
        )


class PostgresCreateSessionRepository(CreateSessionRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_provision_session(
        self, lab_id: UUID, actor_id: UUID, actor_role: str
    ) -> CreateSessionResult:
        session = SessionModel(
            lab_id=lab_id,
            state=SessionState.PROVISIONING.value,
            last_transition_actor=actor_role,
            last_transition_reason=None,
        )
        self._db.add(session)
        self._db.flush()
        self._db.refresh(session)

        return CreateSessionResult(
            session_id=session.id,
            lab_id=lab_id,
            lab_version_id=session.lab_version_id,
            state=session.state,
            resume_mode=session.resume_mode,
            created_at=session.created_at,
            requester_user_id=actor_id,
        )
