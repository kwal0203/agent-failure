import logging
from datetime import datetime
from uuid import UUID

from apps.contracts.src.idempotency import (
    build_session_completed_event_idempotency_key,
)
from pydantic import ValidationError

from .ports import (
    LabObjectiveTemplateReaderPort,
    OutboxSessionObjectiveCompletedPort,
    SessionCompletionEventOutboxPort,
    SessionCompletionWriterPort,
    SessionObjectiveWriterPort,
)
from .schemas import ObjectiveCompletedEventPayload
from .types import SessionObjectiveProjectionOnceResult

logger = logging.getLogger(__name__)

LAB_COMPLETION_REASON_ALL_REQUIRED_OBJECTIVES_COMPLETED = (
    "ALL_REQUIRED_OBJECTIVES_COMPLETED"
)


def initialize_session_objectives(
    *,
    session_id: UUID,
    lab_version_id: UUID,
    template_reader: LabObjectiveTemplateReaderPort,
    objective_writer: SessionObjectiveWriterPort,
) -> int:
    """
    Materialize objective templates for a session.

    Returns the number of templates processed.
    """
    templates = template_reader.list_objective_templates(lab_version_id=lab_version_id)

    for objective_key, label, sort_order in templates:
        objective_writer.upsert_objective(
            session_id=session_id,
            objective_key=objective_key,
            label=label,
            sort_order=sort_order,
        )

    return len(templates)


def process_pending_objective_completed_once(
    *,
    outbox_repo: OutboxSessionObjectiveCompletedPort,
    event_outbox_repo: SessionCompletionEventOutboxPort,
    template_reader: LabObjectiveTemplateReaderPort,
    objective_writer: SessionObjectiveWriterPort,
    completion_writer: SessionCompletionWriterPort,
) -> SessionObjectiveProjectionOnceResult:
    events = outbox_repo.claim_pending_objective_completed()
    claimed_count = len(events)
    succeeded_count = 0
    failed_count = 0
    retried_count = 0

    for event in events:
        try:
            payload = ObjectiveCompletedEventPayload.model_validate(event.payload)
        except ValidationError as exc:
            outbox_repo.mark_terminal_failure(
                outbox_event_id=event.outbox_event_id,
                error_message=f"INVALID_OUTBOX_PAYLOAD: {exc}",
            )
            failed_count += 1
            continue

        try:
            objective_writer.mark_complete(
                session_id=payload.session_id,
                objective_key=payload.objective_key,
                completed_at=payload.occurred_at,
            )
            _apply_completion_policy_after_objective_projection(
                session_id=payload.session_id,
                lab_id=payload.lab_id,
                lab_version_id=payload.lab_version_id,
                objective_writer=objective_writer,
                template_reader=template_reader,
                completion_writer=completion_writer,
                event_outbox_repo=event_outbox_repo,
                completed_at=payload.occurred_at,
                trigger_objective_key=payload.objective_key,
                trigger_reason_code=payload.reason_code,
                trigger_event_index=payload.trigger_event_index,
            )
            outbox_repo.mark_processed(outbox_event_id=event.outbox_event_id)
            succeeded_count += 1
        except Exception as exc:
            outbox_repo.mark_retryable_failure(
                outbox_event_id=event.outbox_event_id,
                error_message=str(exc),
            )
            retried_count += 1

    return SessionObjectiveProjectionOnceResult(
        claimed_count=claimed_count,
        succeeded_count=succeeded_count,
        failed_count=failed_count,
        retried_count=retried_count,
    )


def _apply_completion_policy_after_objective_projection(
    *,
    session_id: UUID,
    lab_id: UUID,
    lab_version_id: UUID,
    objective_writer: SessionObjectiveWriterPort,
    template_reader: LabObjectiveTemplateReaderPort,
    completion_writer: SessionCompletionWriterPort,
    event_outbox_repo: SessionCompletionEventOutboxPort,
    completed_at: datetime,
    trigger_objective_key: str,
    trigger_reason_code: str,
    trigger_event_index: int,
) -> None:
    template_rows = template_reader.list_objective_templates(
        lab_version_id=lab_version_id
    )
    required_keys = {objective_key for objective_key, _, _ in template_rows}
    if not required_keys:
        return

    objective_states = objective_writer.list_objective_states(session_id=session_id)
    status_by_key = {
        objective_key: status for objective_key, status in objective_states
    }
    completed_keys = {
        objective_key
        for objective_key, status in status_by_key.items()
        if status == "complete"
    }
    all_required_complete = all(
        status_by_key.get(objective_key) == "complete"
        for objective_key in required_keys
    )
    if not all_required_complete:
        return

    completion_persisted = completion_writer.mark_completion_if_in_progress(
        session_id=session_id,
        completion_status="completed_success",
        completed_at=completed_at,
        completion_reason_code=LAB_COMPLETION_REASON_ALL_REQUIRED_OBJECTIVES_COMPLETED,
    )
    if completion_persisted:
        event_outbox_repo.enqueue_session_completed(
            session_id=session_id,
            lab_id=lab_id,
            lab_version_id=lab_version_id,
            outcome="completed_success",
            completion_reason_code=LAB_COMPLETION_REASON_ALL_REQUIRED_OBJECTIVES_COMPLETED,
            trigger_event_index=trigger_event_index,
            idempotency_key=build_session_completed_event_idempotency_key(
                session_id=session_id,
                outcome="completed_success",
                completion_reason_code=LAB_COMPLETION_REASON_ALL_REQUIRED_OBJECTIVES_COMPLETED,
                trigger_event_index=trigger_event_index,
            ),
            occurred_at=completed_at,
        )
    logger.info(
        "session completion evaluated session_id=%s lab_version_id=%s "
        "trigger_objective_key=%s trigger_reason_code=%s trigger_event_index=%s "
        "required_objective_keys=%s completed_objective_keys=%s completion_reason_code=%s "
        "completion_persisted=%s",
        session_id,
        lab_version_id,
        trigger_objective_key,
        trigger_reason_code,
        trigger_event_index,
        sorted(required_keys),
        sorted(completed_keys),
        LAB_COMPLETION_REASON_ALL_REQUIRED_OBJECTIVES_COMPLETED,
        completion_persisted,
    )
