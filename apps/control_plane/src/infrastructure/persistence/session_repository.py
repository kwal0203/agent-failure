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
    SessionMetadataRow,
)

from apps.control_plane.src.domain.session_lifecycle.state_machine import (
    SessionState,
    Trigger,
)
from apps.control_plane.src.application.orchestrator.ports import (
    ReconciliationSessionQueryPort,
    ExpirySessionPort,
)
from apps.control_plane.src.application.orchestrator.types import (
    ExpiryCandidate,
    ReconciliationCandidate,
)
from apps.control_plane.src.application.trace.ports import TraceEventPort
from apps.control_plane.src.application.trace.types import TraceEvent
from apps.control_plane.src.infrastructure.persistence.models import (
    EvaluatorResultModel,
)
from apps.control_plane.src.application.evaluator_feedback.ports import EvaluatorPort
from apps.control_plane.src.application.evaluator_feedback.types import (
    EvaluatorPersistedResult,
    ResultType,
    FeedbackLevel,
)

from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session
from sqlalchemy import select, update, and_, or_, func
from datetime import datetime, timezone
from typing import Mapping, cast
from uuid import UUID, uuid4

from .models import SessionModel, SessionTransitionEventModel, TraceEventModel
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

        return SessionRow(
            id=row.id, runtime_id=row.runtime_id, state=SessionState(row.state)
        )

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

    def get_session_metadata(self, session_id: UUID) -> SessionMetadataRow | None:
        stmt = select(SessionModel).where(SessionModel.id == session_id)
        result = self._db.execute(statement=stmt).scalar_one_or_none()
        if result is None:
            return None

        # TODO(P2-EA-T4): This currently reads denormalized reason from
        # sessions.last_transition_reason for fast metadata responses.
        # Long-term, query/project latest reason + metadata from
        # session_transition_events as the source of truth.
        return SessionMetadataRow(
            id=result.id,
            lab_id=result.lab_id,
            lab_version_id=result.lab_version_id,
            owner_user_id=result.owner_user_id,
            state=result.state,
            runtime_substate=result.runtime_substate,
            resume_mode=result.resume_mode,
            last_transition_reason=result.last_transition_reason,
            created_at=result.created_at,
            started_at=result.started_at,
            ended_at=result.ended_at,
        )


class SQLAlchemyCreateSessionRepository(CreateSessionRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_provision_session(
        self, lab_id: UUID, actor_id: UUID, actor_role: str
    ) -> CreateSessionResult:
        session = SessionModel(
            lab_id=lab_id,
            # TODO(E4 follow-up): replace placeholder lab_version_id assignment
            # with real lab-version binding at launch time.
            lab_version_id=uuid4(),
            owner_user_id=actor_id,
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


class SQLAlchemyReconciliationSessionRepository(ReconciliationSessionQueryPort):
    CANDIDATE_STATES: tuple[str, ...] = ("ACTIVE", "PROVISIONING")
    CANDIDATE_TERMINAL_STATES: tuple[str, ...] = (
        "COMPLETED",
        "FAILED",
        "EXPIRED",
        "CANCELLED",
    )

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_reconciliation_candidates(
        self, *, limit: int = 100
    ) -> list[ReconciliationCandidate]:
        candidate_rows = (
            self._db.execute(
                select(SessionModel)
                .where(
                    or_(
                        SessionModel.state.in_(self.CANDIDATE_STATES),
                        and_(
                            SessionModel.state.in_(self.CANDIDATE_TERMINAL_STATES),
                            SessionModel.runtime_id.is_not(None),
                        ),
                    )
                )
                .order_by(SessionModel.created_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )

        candidates: list[ReconciliationCandidate] = []
        for row in candidate_rows:
            candidates.append(
                ReconciliationCandidate(
                    state=row.state,
                    session_id=row.id,
                    runtime_id=row.runtime_id,
                    runtime_substate=row.runtime_substate,
                )
            )

        return candidates


class SQLAlchemyExpirySessionRepository(ExpirySessionPort):
    CANDIDATE_STATES: tuple[str, ...] = ("PROVISIONING", "ACTIVE", "IDLE")

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_expiry_candidates(self, *, limit: int = 100) -> list[ExpiryCandidate]:
        candidate_rows = (
            self._db.execute(
                select(SessionModel)
                .where(SessionModel.state.in_(self.CANDIDATE_STATES))
                .order_by(SessionModel.created_at.desc())
                .limit(limit)
            )
            .scalars()
            .all()
        )

        candidates: list[ExpiryCandidate] = []
        for row in candidate_rows:
            candidates.append(
                ExpiryCandidate(
                    state=row.state,
                    session_id=row.id,
                    created_at=row.created_at,
                    started_at=row.started_at,
                    ended_at=row.ended_at,
                )
            )

        return candidates


class SQLAlchemyTraceEventRepository(TraceEventPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def append_trace_event(self, trace: TraceEvent) -> None:
        event = TraceEventModel(
            event_id=trace.event_id,
            session_id=trace.session_id,
            family=trace.family,
            event_type=trace.event_type,
            occurred_at=trace.occurred_at,
            source=trace.source,
            event_index=trace.event_index,
            payload=trace.payload,
            trace_version=trace.trace_version,
            correlation_id=trace.correlation_id,
            request_id=trace.request_id,
            actor_user_id=trace.actor_user_id,
            lab_id=trace.lab_id,
            lab_version_id=trace.lab_version_id,
        )

        self._db.add(event)
        self._db.flush()

    def get_next_event_index(self, session_id: UUID) -> int:
        max_index = self._db.execute(
            select(func.max(TraceEventModel.event_index)).where(
                TraceEventModel.session_id == session_id
            )
        ).scalar_one_or_none()

        if max_index is None:
            return 0

        return int(max_index) + 1


class SQLAlchemyEvaluatorRepository(EvaluatorPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def list_results_for_session(
        self, session_id: UUID
    ) -> tuple[EvaluatorPersistedResult, ...]:
        rows = (
            self._db.execute(
                select(EvaluatorResultModel)
                .where(EvaluatorResultModel.session_id == session_id)
                .order_by(
                    EvaluatorResultModel.created_at, EvaluatorResultModel.id.asc()
                )
            )
            .scalars()
            .all()
        )

        result: list[EvaluatorPersistedResult] = []
        for row in rows:
            result.append(
                EvaluatorPersistedResult(
                    id=row.id,
                    idempotency_key=row.idempotency_key,
                    result_type=cast(ResultType, row.result_type),
                    code=row.code,
                    trigger_event_index=row.trigger_event_index,
                    trigger_start_event_index=row.trigger_start_event_index,
                    trigger_end_event_index=row.trigger_end_event_index,
                    feedback_level=cast(FeedbackLevel, row.feedback_level),
                    reason_code=row.reason_code,
                    feedback_payload=row.feedback_payload,
                    created_at=row.created_at,
                    session_id=row.session_id,
                    lab_id=row.lab_id,
                    lab_version_id=row.lab_version_id,
                    evaluator_version=row.evaluator_version,
                )
            )

        return tuple(result)
