from apps.evaluator.src.application.ports import EvaluatorOutboxPort
from apps.evaluator.src.application.types import (
    PendingEvaluatorEvent,
    EvaluatorTaskInput,
)
from apps.control_plane.src.infrastructure.persistence.models import OutboxEventModel

from sqlalchemy.orm import Session
from sqlalchemy import select

from datetime import datetime, timezone
from uuid import UUID


def _as_uuid(value: object, field: str) -> UUID:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        return UUID(value)
    raise ValueError(f"Invalid {field}: {value!r}")


def _as_int(value: object, field: str) -> int:
    if isinstance(value, int):
        return value
    raise ValueError(f"Invalid {field}: {value!r}")


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

            payload = row.payload
            try:
                task = EvaluatorTaskInput(
                    session_id=row.aggregate_id,
                    lab_id=_as_uuid(payload.get("lab_id"), "lab_id"),
                    lab_version_id=_as_uuid(
                        payload.get("lab_version_id"), "lab_version_id"
                    ),
                    evaluator_version=_as_int(
                        payload.get("evaluator_version"), "evaluator_version"
                    ),
                    start_event_index=_as_int(
                        payload.get("start_event_index"), "start_event_index"
                    ),
                    end_event_index=_as_int(
                        payload.get("end_event_index"), "end_event_index"
                    ),
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
