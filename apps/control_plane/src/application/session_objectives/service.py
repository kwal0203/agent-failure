from uuid import UUID

from pydantic import ValidationError

from .ports import (
    LabObjectiveTemplateReaderPort,
    OutboxSessionObjectiveCompletedPort,
    SessionObjectiveWriterPort,
)
from .schemas import ObjectiveCompletedEventPayload
from .types import SessionObjectiveProjectionOnceResult


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
    objective_writer: SessionObjectiveWriterPort,
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
