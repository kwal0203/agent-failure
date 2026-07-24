from datetime import datetime, timezone
from typing import Mapping
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from apps.contracts.src.schemas import (
    SessionEvaluateRequestedPayload,
    SessionCompletedEventPayload,
    SessionCompletedOutboxEvent,
)
from apps.contracts.src.types import (
    CompletionOutcome,
    OUTBOX_EVENT_SESSION_CLEANUP_REQUESTED,
    OUTBOX_EVENT_SESSION_COMPLETED,
    OUTBOX_EVENT_SESSION_EVALUATE_REQUESTED,
    OUTBOX_EVENT_SESSION_HINT_UNLOCKED,
    OUTBOX_EVENT_SESSION_OBJECTIVE_COMPLETED,
    OUTBOX_EVENT_SESSION_PUBLISH_FEEDBACK,
    OUTBOX_EVENT_SESSION_TRANSITIONED,
)

from apps.control_plane.src.application.session_hints.schemas import (
    HintUnlockedEventPayload,
)
from apps.control_plane.src.application.session_lifecycle.ports import Outbox
from apps.control_plane.src.domain.session_lifecycle.state_machine import (
    SessionState,
    Trigger,
)
from .models import OutboxEventModel


class SQLAlchemyOutbox(Outbox):
    def __init__(self, db: Session) -> None:
        self._db = db

    def enqueue_for_transition(
        self,
        session_id: UUID,
        prev_state: SessionState,
        next_state: SessionState,
        trigger: Trigger,
        metadata: Mapping[str, object],
        transition_id: UUID,
    ) -> None:
        payload: dict[str, object] = {
            "session_id": str(session_id),
            "prev_state": prev_state.value,
            "next_state": next_state.value,
            "trigger": trigger.value,
            "metadata": dict(metadata),
            "transition_id": str(transition_id),
        }

        event = OutboxEventModel(
            event_type=OUTBOX_EVENT_SESSION_TRANSITIONED,
            aggregate_id=session_id,
            payload=payload,
        )
        self._db.add(event)

    def enqueue_for_cleanup(
        self,
        session_id: UUID,
        runtime_id: str | None,
        terminal_state: str | None,
        reason_code: str | None,
        requested_at: datetime | None,
    ) -> None:
        payload: dict[str, object] = {
            "session_id": str(session_id),
            "runtime_id": runtime_id,
            "terminal_state": terminal_state,
            "reason_code": reason_code,
            "requested_at": requested_at.isoformat() if requested_at else None,
        }

        event = OutboxEventModel(
            event_type=OUTBOX_EVENT_SESSION_CLEANUP_REQUESTED,
            aggregate_id=session_id,
            payload=payload,
        )

        self._db.add(event)

    def enqueue_for_evaluator(
        self,
        *,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        evaluator_version: int,
        start_event_index: int,
        end_event_index: int,
        requested_at: datetime | None = None,
    ) -> None:
        payload_model = SessionEvaluateRequestedPayload(
            lab_id=lab_id,
            lab_version_id=lab_version_id,
            evaluator_version=evaluator_version,
            start_event_index=start_event_index,
            end_event_index=end_event_index,
        )
        payload: dict[str, object] = payload_model.model_dump(mode="json")

        event = OutboxEventModel(
            event_type=OUTBOX_EVENT_SESSION_EVALUATE_REQUESTED,
            aggregate_id=session_id,
            payload=payload,
        )

        self._db.add(event)

    def enqueue_learner_feedback_publish_request(
        self,
        *,
        session_id: UUID,
        requested_at: datetime | None = None,
    ) -> None:
        payload: dict[str, object] = {
            "session_id": str(session_id),
            "published_at": requested_at.isoformat() if requested_at else None,
        }

        event = OutboxEventModel(
            event_type=OUTBOX_EVENT_SESSION_PUBLISH_FEEDBACK,
            aggregate_id=session_id,
            payload=payload,
        )

        self._db.add(event)

    def enqueue_session_objective_completed(
        self,
        *,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        objective_key: str,
        reason_code: str,
        trigger_event_index: int,
        idempotency_key: str,
        source: str = "control_plane",
        evaluator_version: int | None = None,
        occurred_at: datetime | None = None,
    ) -> None:
        existing = (
            self._db.execute(
                select(OutboxEventModel.id).where(
                    OutboxEventModel.event_type
                    == OUTBOX_EVENT_SESSION_OBJECTIVE_COMPLETED,
                    OutboxEventModel.aggregate_id == session_id,
                    OutboxEventModel.payload["idempotency_key"].astext
                    == idempotency_key,
                )
            )
            .scalars()
            .first()
        )
        if existing is not None:
            return

        payload: dict[str, object] = {
            "session_id": str(session_id),
            "lab_id": str(lab_id),
            "lab_version_id": str(lab_version_id),
            "objective_key": objective_key,
            "reason_code": reason_code,
            "trigger_event_index": trigger_event_index,
            "occurred_at": (occurred_at or datetime.now(timezone.utc)).isoformat(),
            "idempotency_key": idempotency_key,
            "source": source,
            "evaluator_version": evaluator_version,
        }

        event = OutboxEventModel(
            event_type=OUTBOX_EVENT_SESSION_OBJECTIVE_COMPLETED,
            aggregate_id=session_id,
            payload=payload,
        )
        self._db.add(event)

    def enqueue_session_hint_unlocked(
        self,
        *,
        session_id: UUID,
        hint_key: str,
        text: str,
        sort_order: int,
        unlocked_at: datetime,
        idempotency_key: str,
    ) -> None:
        existing = (
            self._db.execute(
                select(OutboxEventModel.id).where(
                    OutboxEventModel.event_type == OUTBOX_EVENT_SESSION_HINT_UNLOCKED,
                    OutboxEventModel.aggregate_id == session_id,
                    OutboxEventModel.payload["idempotency_key"].astext
                    == idempotency_key,
                )
            )
            .scalars()
            .first()
        )
        if existing is not None:
            return

        payload_model = HintUnlockedEventPayload(
            session_id=session_id,
            hint_key=hint_key,
            text=text,
            sort_order=sort_order,
            unlocked_at=unlocked_at,
            idempotency_key=idempotency_key,
        )
        payload = payload_model.model_dump(mode="json")

        event = OutboxEventModel(
            event_type=OUTBOX_EVENT_SESSION_HINT_UNLOCKED,
            aggregate_id=session_id,
            payload=payload,
        )
        self._db.add(event)

    def enqueue_session_completed(
        self,
        *,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        outcome: CompletionOutcome,
        completion_reason_code: str | None,
        trigger_event_index: int | None,
        idempotency_key: str,
        occurred_at: datetime | None = None,
    ) -> None:
        existing = (
            self._db.execute(
                select(OutboxEventModel.id).where(
                    OutboxEventModel.event_type == OUTBOX_EVENT_SESSION_COMPLETED,
                    OutboxEventModel.aggregate_id == session_id,
                    OutboxEventModel.payload["idempotency_key"].astext
                    == idempotency_key,
                )
            )
            .scalars()
            .first()
        )
        if existing is not None:
            return

        payload_model = SessionCompletedEventPayload(
            session_id=session_id,
            lab_id=lab_id,
            lab_version_id=lab_version_id,
            outcome=outcome,
            completion_reason_code=completion_reason_code,
            trigger_event_index=trigger_event_index,
            occurred_at=occurred_at or datetime.now(timezone.utc),
            idempotency_key=idempotency_key,
        )
        outbox_event_model = SessionCompletedOutboxEvent(
            aggregate_id=session_id,
            payload=payload_model,
        )

        # Keep nullable payload fields present for replay/audit fidelity.
        payload = outbox_event_model.payload.model_dump(
            mode="json",
            exclude_none=False,
        )

        event = OutboxEventModel(
            event_type=outbox_event_model.event_type,
            aggregate_id=outbox_event_model.aggregate_id,
            payload=payload,
        )
        self._db.add(event)
