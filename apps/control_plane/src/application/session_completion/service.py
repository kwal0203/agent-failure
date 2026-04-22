from pydantic import ValidationError

from apps.contracts.src.schemas import SessionCompletedOutboxEvent

from .ports import OutboxSessionCompletedPort, SessionCompletionWriterPort
from .types import SessionCompletionProjectionOnceResult


def process_pending_session_completed_once(
    *,
    outbox_repo: OutboxSessionCompletedPort,
    completion_writer: SessionCompletionWriterPort,
) -> SessionCompletionProjectionOnceResult:
    events = outbox_repo.claim_pending_session_completed()
    claimed_count = len(events)
    succeeded_count = 0
    failed_count = 0
    retried_count = 0

    for event in events:
        try:
            outbox_event = SessionCompletedOutboxEvent.model_validate(
                {
                    "event_type": "session.completed.v1",
                    "aggregate_id": event.session_id,
                    "payload": event.payload,
                }
            )
        except ValidationError as exc:
            outbox_repo.mark_terminal_failure(
                outbox_event_id=event.outbox_event_id,
                error_message=f"INVALID_OUTBOX_PAYLOAD: {exc}",
            )
            failed_count += 1
            continue
        payload = outbox_event.payload

        if payload.session_id != event.session_id:
            outbox_repo.mark_terminal_failure(
                outbox_event_id=event.outbox_event_id,
                error_message=(
                    "INVALID_OUTBOX_PAYLOAD: payload.session_id does not match "
                    "event aggregate_id"
                ),
            )
            failed_count += 1
            continue

        try:
            completion_writer.mark_completion_if_in_progress(
                session_id=payload.session_id,
                completion_status=payload.outcome,
                completed_at=payload.occurred_at,
                completion_reason_code=payload.completion_reason_code,
            )
            outbox_repo.mark_processed(outbox_event_id=event.outbox_event_id)
            succeeded_count += 1
        except Exception as exc:
            outbox_repo.mark_retryable_failure(
                outbox_event_id=event.outbox_event_id,
                error_message=str(exc),
            )
            retried_count += 1

    return SessionCompletionProjectionOnceResult(
        claimed_count=claimed_count,
        succeeded_count=succeeded_count,
        failed_count=failed_count,
        retried_count=retried_count,
    )
