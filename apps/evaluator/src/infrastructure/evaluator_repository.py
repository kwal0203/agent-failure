from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import CursorResult
from typing import cast, Any

from apps.evaluator.src.application.ports import EvaluatorPort
from apps.evaluator.src.application.types import (
    EvaluatorRunResult,
    EvaluatorTaskInput,
    EvaluatorTraceEvent,
    EvaluatorFinding,
)
from apps.control_plane.src.infrastructure.persistence.models import (
    TraceEventModel,
    EvaluatorResultModel,
)
from uuid import uuid4, UUID


class SQLAlchemyEvaluatorRepository(EvaluatorPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def evaluate_trace_window(self, input: EvaluatorTaskInput) -> EvaluatorRunResult:
        start_event_index = input.start_event_index  # int
        end_event_index = input.end_event_index  # int

        if start_event_index < 0 or end_event_index < start_event_index:
            raise ValueError("Invalid event window")

        events = self.load_events(input=input)
        if any(
            event.lab_id is not None and event.lab_id != input.lab_id
            for event in events
        ):
            raise ValueError("Trace event lab_id does not match evaluator task lab_id")

        if any(
            event.lab_version_id is not None
            and event.lab_version_id != input.lab_version_id
            for event in events
        ):
            raise ValueError(
                "Trace event lab_version_id does not match evaluator task lab_version_id"
            )

        if any(event.session_id != input.session_id for event in events):
            raise ValueError(
                "Trace event session_id does not match evaluator task session_id"
            )

        findings: tuple[EvaluatorFinding, ...] = self.run_rules(events=events)
        return EvaluatorRunResult(
            session_id=input.session_id,
            lab_id=input.lab_id,
            lab_version_id=input.lab_version_id,
            evaluator_version=input.evaluator_version,
            start_event_index=input.start_event_index,
            end_event_index=input.end_event_index,
            evaluated_event_count=len(events),
            findings_count=len(findings),
            no_op=len(findings) == 0,
            findings=findings,
        )

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

    def run_rules(
        self, events: list[EvaluatorTraceEvent]
    ) -> tuple[EvaluatorFinding, ...]:
        findings: list[EvaluatorFinding] = []
        for event in events:
            finding = self._rule_runtime_provision_failed(event=event)
            if finding is not None:
                findings.append(finding)
                continue

            finding = self._rule_model_turn_failed(event=event)
            if finding is not None:
                findings.append(finding)

        return tuple(findings)

    def _rule_runtime_provision_failed(
        self, event: EvaluatorTraceEvent
    ) -> EvaluatorFinding | None:
        if event.event_type != "RUNTIME_PROVISION_FAILED":
            return None

        return EvaluatorFinding(
            result_type="constraint_violation",
            code="runtime.provision_failed",
            trigger_event_index=event.event_index,
            trigger_start_event_index=None,
            trigger_end_event_index=None,
            feedback_level="flag",
            reason_code="RUNTIME_PROVISION_FAILED",
            feedback_payload={"event_type": event.event_type, "family": event.family},
        )

    def _rule_model_turn_failed(
        self, event: EvaluatorTraceEvent
    ) -> EvaluatorFinding | None:
        if event.event_type != "MODEL_TURN_FAILED":
            return None

        return EvaluatorFinding(
            result_type="constraint_violation",
            code="model.turn_failed",
            trigger_event_index=event.event_index,
            trigger_start_event_index=None,
            trigger_end_event_index=None,
            feedback_level="flag",
            reason_code="MODEL_TURN_FAILED",
            feedback_payload={"event_type": event.event_type, "family": event.family},
        )

    def persist_result_if_new(
        self,
        idempo_key: str,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        evaluator_version: int,
        finding: EvaluatorFinding,
    ) -> bool:
        rows = self._db.execute(
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
        )

        result = cast(CursorResult[Any], rows)
        return result.rowcount == 1
