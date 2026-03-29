from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from typing import cast

from apps.evaluator.src.application.ports import EvaluatorPort
from apps.evaluator.src.application.types import (
    EvaluatorPersistedResult,
    EvaluatorTaskInput,
    EvaluatorTraceEvent,
    EvaluatorFinding,
    ResultType,
    FeedbackLevel,
)
from apps.control_plane.src.infrastructure.persistence.models import (
    TraceEventModel,
    EvaluatorResultModel,
)
from uuid import uuid4, UUID


class SQLAlchemyEvaluatorRepository(EvaluatorPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def load_events(self, input: EvaluatorTaskInput) -> list[EvaluatorTraceEvent]:
        event_rows = (
            self._db.execute(
                select(TraceEventModel)
                .where(
                    TraceEventModel.session_id == input.session_id,
                    TraceEventModel.event_index >= input.start_event_index,
                    TraceEventModel.event_index <= input.end_event_index,
                )
                .order_by(TraceEventModel.event_index.asc())
            )
            .scalars()
            .all()
        )

        trace_events: list[EvaluatorTraceEvent] = []
        for row in event_rows:
            trace_events.append(
                EvaluatorTraceEvent(
                    event_id=row.event_id,
                    session_id=row.session_id,
                    family=row.family,
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

        return trace_events

    def persist_result_if_new(
        self,
        idempo_key: str,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        evaluator_version: int,
        finding: EvaluatorFinding,
    ) -> bool:
        stmt = (
            pg_insert(EvaluatorResultModel)
            .values(
                id=uuid4(),
                idempotency_key=idempo_key,
                result_type=finding.result_type,
                code=finding.code,
                trigger_event_index=finding.trigger_event_index,
                trigger_start_event_index=finding.trigger_start_event_index,
                trigger_end_event_index=finding.trigger_end_event_index,
                feedback_level=finding.feedback_level,
                reason_code=finding.reason_code,
                feedback_payload=finding.feedback_payload,
                session_id=session_id,
                lab_id=lab_id,
                lab_version_id=lab_version_id,
                evaluator_version=evaluator_version,
            )
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
            .returning(EvaluatorResultModel.id)
        )

        inserted_id = self._db.execute(stmt).scalar_one_or_none()
        return inserted_id is not None

    def list_results_for_session(
        self, session_id: UUID
    ) -> list[EvaluatorPersistedResult]:
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

        return result
