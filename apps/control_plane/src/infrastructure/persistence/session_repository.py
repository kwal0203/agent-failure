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
)
from apps.control_plane.src.application.session_query.types import (
    SessionFeedbackRow,
    SessionHintRow,
    SessionMetadataRow,
    SessionObjectiveRow,
    SessionMetadataBundleRow,
)
from apps.control_plane.src.application.session_query.helpers import (
    parse_completion_status,
    parse_feedback_severity,
    parse_hint_status,
    parse_progress_status,
)
from apps.control_plane.src.application.session_completion.guard import (
    evaluate_completion_transition,
)
from apps.control_plane.src.application.session_completion.types import (
    CompletionStatus,
    SessionCompletionState,
)

from apps.control_plane.src.domain.session_lifecycle.state_machine import (
    SessionState,
    Trigger,
)
from apps.control_plane.src.application.orchestrator.ports import (
    ReconciliationSessionQueryPort,
    ExpirySessionPort,
    SessionRuntimeBindingPort,
)
from apps.control_plane.src.application.orchestrator.types import (
    ExpiryCandidate,
    ReconciliationCandidate,
    UpsertSessionRuntimeBindingInput,
    SessionRuntimeBinding,
    RuntimeKind,
    RuntimeBindingStatus,
)
from apps.control_plane.src.application.trace.ports import TraceEventPort
from apps.control_plane.src.application.trace.types import TraceEvent, TraceFamily
from apps.control_plane.src.infrastructure.persistence.models import (
    EvaluatorResultModel,
    SessionRuntimeBindingModel,
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

from .models import (
    SessionModel,
    SessionTransitionEventModel,
    TraceEventModel,
    SessionHintModel,
    SessionObjectiveModel,
    SessionFeedbackModel,
)
from .errors import StateMismatch
from .session_feedback_ordering import session_feedback_ordering


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

    def mark_completion_if_in_progress(
        self,
        *,
        session_id: UUID,
        completion_status: CompletionStatus,
        completed_at: datetime,
        completion_reason_code: str | None,
    ) -> bool:
        current_status_result = self._db.execute(
            select(SessionModel.completion_status).where(SessionModel.id == session_id)
        ).scalar_one_or_none()
        if current_status_result is None:
            return False
        current_status = parse_completion_status(current_status_result)
        decision = evaluate_completion_transition(
            current_status=current_status,
            requested_status=completion_status,
        )
        if not decision.should_apply:
            return False

        stmt = (
            update(SessionModel)
            .where(
                SessionModel.id == session_id,
                SessionModel.completion_status == current_status,
            )
            .values(
                completion_status=completion_status,
                completed_at=completed_at,
                completion_reason_code=completion_reason_code,
            )
        )
        result = cast(CursorResult[object], self._db.execute(stmt))
        return result.rowcount == 1

    def get_completion_state(
        self, *, session_id: UUID
    ) -> SessionCompletionState | None:
        row = self._db.execute(
            select(
                SessionModel.completion_status,
                SessionModel.completed_at,
                SessionModel.completion_reason_code,
            ).where(SessionModel.id == session_id)
        ).one_or_none()
        if row is None:
            return None
        return SessionCompletionState(
            completion_status=parse_completion_status(row.completion_status),
            completed_at=row.completed_at,
            completion_reason_code=row.completion_reason_code,
        )

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

    def get_session_metadata(self, session_id: UUID) -> SessionMetadataBundleRow | None:
        session_stmt = select(SessionModel).where(SessionModel.id == session_id)
        session_model = self._db.execute(statement=session_stmt).scalar_one_or_none()
        if session_model is None:
            return None

        objectives_stmt = (
            select(SessionObjectiveModel)
            .where(SessionObjectiveModel.session_id == session_id)
            .order_by(SessionObjectiveModel.sort_order.asc())
        )
        objective_models = self._db.execute(statement=objectives_stmt).scalars().all()
        hints_stmt = select(SessionHintModel).where(
            SessionHintModel.session_id == session_id
        )
        hint_models = self._db.execute(statement=hints_stmt).scalars().all()
        feedback_stmt = (
            select(SessionFeedbackModel)
            .where(SessionFeedbackModel.session_id == session_id)
            .order_by(*session_feedback_ordering())
        )
        feedback_models = self._db.execute(statement=feedback_stmt).scalars().all()

        session_metadata = SessionMetadataRow(
            id=session_model.id,
            lab_id=session_model.lab_id,
            lab_version_id=session_model.lab_version_id,
            lab_difficulty=session_model.lab_difficulty,
            owner_user_id=session_model.owner_user_id,
            state=session_model.state,
            runtime_substate=session_model.runtime_substate,
            resume_mode=session_model.resume_mode,
            last_transition_reason=session_model.last_transition_reason,
            created_at=session_model.created_at,
            started_at=session_model.started_at,
            ended_at=session_model.ended_at,
            completion_status=parse_completion_status(session_model.completion_status),
            completed_at=session_model.completed_at,
            completion_reason_code=session_model.completion_reason_code,
        )
        progress_chips = [
            SessionObjectiveRow(
                objective_key=obj.objective_key,
                label=obj.label,
                status=parse_progress_status(obj.status),
                completed_at=obj.completed_at,
                updated_at=obj.updated_at,
            )
            for obj in objective_models
        ]
        hints = [
            SessionHintRow(
                hint_key=hint.hint_key,
                text=hint.text,
                sort_order=hint.sort_order,
                status=parse_hint_status(hint.status),
                unlock_at=hint.unlock_at,
                unlocked_at=hint.unlocked_at,
                seen_at=hint.seen_at,
            )
            for hint in hint_models
        ]
        hints.sort(
            key=lambda hint: (
                0 if hint.status == "unlocked" else 1,
                hint.unlocked_at if hint.status == "unlocked" else hint.unlock_at,
                hint.sort_order,
                hint.hint_key,
            )
        )
        feedback = [
            SessionFeedbackRow(
                id=feedback_row.id,
                feedback_key=feedback_row.feedback_key,
                reason_code=feedback_row.reason_code,
                message=feedback_row.message,
                severity=parse_feedback_severity(feedback_row.severity),
                trigger_event_index=feedback_row.trigger_event_index,
                created_at=feedback_row.created_at,
                seen_at=feedback_row.seen_at,
            )
            for feedback_row in feedback_models
        ]

        return SessionMetadataBundleRow(
            metadata=session_metadata,
            objectives=progress_chips,
            hints=hints,
            feedback=feedback,
        )


class SQLAlchemyCreateSessionRepository(CreateSessionRepository):
    def __init__(self, db: Session) -> None:
        self._db = db

    def create_provision_session(
        self,
        lab_id: UUID,
        lab_version_id: UUID,
        lab_difficulty: str,
        actor_id: UUID,
        actor_role: str,
    ) -> CreateSessionResult:
        session = SessionModel(
            lab_id=lab_id,
            lab_version_id=lab_version_id,
            owner_user_id=actor_id,
            state=SessionState.PROVISIONING.value,
            last_transition_actor=actor_role,
            last_transition_reason=None,
            lab_difficulty=lab_difficulty,
            completion_status="in_progress",
            completed_at=None,
            completion_reason_code=None,
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
            lab_difficulty=lab_difficulty,
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
            lab_difficulty=trace.lab_difficulty,
        )

        self._db.add(event)
        self._db.flush()

    def list_trace_events_for_session(self, session_id: UUID) -> tuple[TraceEvent, ...]:
        rows = (
            self._db.execute(
                select(TraceEventModel)
                .where(TraceEventModel.session_id == session_id)
                .order_by(
                    TraceEventModel.event_index.asc(), TraceEventModel.event_id.asc()
                )
            )
            .scalars()
            .all()
        )

        result: list[TraceEvent] = []
        for row in rows:
            result.append(
                TraceEvent(
                    event_id=row.event_id,
                    session_id=row.session_id,
                    family=cast(TraceFamily, row.family),
                    event_type=row.event_type,
                    occurred_at=row.occurred_at,
                    source=row.source,
                    event_index=row.event_index,
                    payload=row.payload,
                    trace_version=row.trace_version,
                    correlation_id=row.correlation_id,
                    request_id=row.request_id,
                    actor_user_id=row.actor_user_id,
                    lab_id=row.lab_id,
                    lab_version_id=row.lab_version_id,
                )
            )

        return tuple(result)

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


class SQLAlchemySessionRuntimeBindingRepository(SessionRuntimeBindingPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def upsert_runtime_binding(
        self, *, input: UpsertSessionRuntimeBindingInput
    ) -> None:
        stmt = (
            select(SessionRuntimeBindingModel)
            .where(SessionRuntimeBindingModel.session_id == input.session_id)
            .with_for_update()
        )

        row = self._db.execute(stmt).scalar_one_or_none()
        if row is None:
            row = SessionRuntimeBindingModel(
                session_id=input.session_id,
                runtime_kind=input.runtime_kind,
                base_url=input.base_url,
                auth_token_ref=input.auth_token_ref,
                status=input.status,
                last_error=input.last_error,
            )
            self._db.add(row)
        else:
            row.runtime_kind = input.runtime_kind
            row.base_url = input.base_url
            row.auth_token_ref = input.auth_token_ref
            row.status = input.status

            if input.status == "ready" and input.last_error is None:
                row.last_error = None
            else:
                row.last_error = input.last_error

        self._db.flush()

    def get_by_session_id(self, *, session_id: UUID) -> SessionRuntimeBinding | None:
        stmt = select(SessionRuntimeBindingModel).where(
            SessionRuntimeBindingModel.session_id == session_id
        )

        # TODO: Can multiple runtimes exists for a session?
        row = self._db.execute(stmt).scalar_one_or_none()
        if row is None:
            return None

        # TODO: These allowed types and statuses should be put in a contract somewhere.
        if row.runtime_kind not in {"k8s_pod"}:
            raise ValueError(f"Unknown runtime kind: {row.runtime_kind}")
        if row.status not in {"provisioning", "ready", "failed", "terminated"}:
            raise ValueError(f"Unknown status: {row.status}")

        return SessionRuntimeBinding(
            session_id=row.session_id,
            runtime_kind=cast(RuntimeKind, row.status),
            base_url=row.base_url,
            auth_token_ref=row.auth_token_ref,
            status=cast(RuntimeBindingStatus, row.status),
            last_error=row.last_error,
        )
