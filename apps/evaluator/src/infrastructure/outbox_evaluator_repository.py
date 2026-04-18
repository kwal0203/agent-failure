from apps.evaluator.src.application.ports import EvaluatorOutboxPort
from apps.evaluator.src.application.types import (
    PendingEvaluatorEvent,
    EvaluatorTaskInput,
    ObjectiveCompletedEvent,
)
from apps.control_plane.src.infrastructure.persistence.models import OutboxEventModel
from apps.evaluator.src.application.schemas import EvaluatorRequestedPayload

from sqlalchemy.orm import Session
from sqlalchemy import select

from datetime import datetime, timezone
from uuid import UUID


class SQLAlchemyOutboxEvaluatorRepository(EvaluatorOutboxPort):
    def __init__(self, db: Session) -> None:
        self._db = db

    def claim_pending_evaluate(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingEvaluatorEvent]:
        ts = now or datetime.now(timezone.utc)
        rows = (
            self._db.execute(
                select(OutboxEventModel)
                .where(
                    OutboxEventModel.event_type == "session.evaluate.requested.v1",
                    OutboxEventModel.status == "pending",
                    OutboxEventModel.available_at <= ts,
                )
                .order_by(OutboxEventModel.created_at.asc(), OutboxEventModel.id.asc())
                .limit(limit=limit)
                .with_for_update(skip_locked=True)
            )
            .scalars()
            .all()
        )

        claimed: list[PendingEvaluatorEvent] = []
        for row in rows:
            row.status = "processing"
            row.processed_at = None
            row.attempt_count += 1
            row.last_error = None

            try:
                p = EvaluatorRequestedPayload.model_validate(row.payload)
                task = EvaluatorTaskInput(
                    session_id=row.aggregate_id,
                    lab_id=p.lab_id,
                    lab_version_id=p.lab_version_id,
                    lab_difficulty=p.lab_difficulty,
                    evaluator_version=p.evaluator_version,
                    start_event_index=p.start_event_index,
                    end_event_index=p.end_event_index,
                )

            except Exception as exc:
                row.status = "failed"
                row.processed_at = ts
                row.last_error = (
                    f"invalid evaluator payload: {type(exc).__name__}: {exc}"
                )
                continue

            claimed.append(
                PendingEvaluatorEvent(
                    outbox_event_id=row.id, task=task, attempt_count=row.attempt_count
                )
            )

        return claimed

    def mark_processed(
        self, *, outbox_event_id: UUID, processed_at: datetime | None = None
    ) -> None:
        row = self._db.get(OutboxEventModel, outbox_event_id)
        if row is None:
            return

        row.status = "processed"
        row.processed_at = processed_at or datetime.now(timezone.utc)
        row.last_error = None

    def mark_terminal_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        failed_at: datetime | None = None,
    ) -> None:
        row = self._db.get(OutboxEventModel, outbox_event_id)
        if row is None:
            return

        row.status = "failed"
        row.processed_at = failed_at or datetime.now(timezone.utc)
        row.last_error = error_message

    def enqueue_learner_feedback_publish_request(
        self,
        *,
        session_id: UUID,
        requested_at: datetime | None = None,
    ) -> None:
        ts = requested_at or datetime.now(timezone.utc)
        payload: dict[str, object] = {
            "session_id": str(session_id),
            "requested_at": ts.isoformat(),
        }

        event = OutboxEventModel(
            event_type="session.publish.feedback.v1",
            aggregate_id=session_id,
            payload=payload,
        )

        self._db.add(event)

    def enqueue_objective_completed_event(
        self, *, event: ObjectiveCompletedEvent
    ) -> None:
        existing = self._db.execute(
            select(OutboxEventModel.id)
            .where(
                OutboxEventModel.event_type == "session.objective.completed.v1",
                OutboxEventModel.aggregate_id == event.session_id,
                OutboxEventModel.payload["idempotency_key"].astext
                == event.idempotency_key,
            )
            .limit(1)
        ).scalar_one_or_none()
        if existing is not None:
            return

        payload: dict[str, object] = {
            "session_id": str(event.session_id),
            "lab_id": str(event.lab_id),
            "lab_version_id": str(event.lab_version_id),
            "objective_key": event.objective_key,
            "reason_code": event.reason_code,
            "trigger_event_index": event.trigger_event_index,
            "occurred_at": event.occurred_at.isoformat(),
            "idempotency_key": event.idempotency_key,
            "source": event.source,
            "evaluator_version": event.evaluator_version,
        }

        outbox_event = OutboxEventModel(
            event_type="session.objective.completed.v1",
            aggregate_id=event.session_id,
            payload=payload,
        )
        self._db.add(outbox_event)
