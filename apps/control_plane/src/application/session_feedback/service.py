from datetime import datetime, timezone
from pydantic import ValidationError
from uuid import UUID

from apps.contracts.src.schemas import SessionFeedbackCreatedOutboxEvent
from apps.contracts.src.types import OUTBOX_EVENT_SESSION_FEEDBACK_CREATED
from apps.control_plane.src.application.common.types import PrincipalContext

from .ports import OutboxSessionFeedbackCreatedPort, SessionFeedbackRepositoryPort
from .errors import (
    ForbiddenErrorSessionFeedback,
    SessionNotFoundErrorSessionFeedback,
)
from .types import (
    SessionFeedbackCreateInput,
    SessionFeedbackProjectionOnceResult,
)


def process_pending_session_feedback_created_once(
    *,
    outbox_repo: OutboxSessionFeedbackCreatedPort,
    feedback_repo: SessionFeedbackRepositoryPort,
) -> SessionFeedbackProjectionOnceResult:
    events = outbox_repo.claim_pending_session_feedback_created()
    claimed_count = len(events)
    succeeded_count = 0
    failed_count = 0
    retried_count = 0

    for event in events:
        try:
            outbox_event = SessionFeedbackCreatedOutboxEvent.model_validate(
                {
                    "event_type": OUTBOX_EVENT_SESSION_FEEDBACK_CREATED,
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
            inserted = feedback_repo.insert_feedback_if_absent(
                input=SessionFeedbackCreateInput(
                    session_id=payload.session_id,
                    feedback_key=payload.feedback_key,
                    reason_code=payload.reason_code,
                    message=payload.message,
                    severity=payload.severity,
                    trigger_event_index=payload.trigger_event_index,
                    created_at=payload.created_at,
                    idempotency_key=payload.idempotency_key,
                )
            )
            # Duplicate semantic feedback (same idempotency key) is a stable no-op.
            if not inserted:
                pass
            outbox_repo.mark_processed(outbox_event_id=event.outbox_event_id)
            succeeded_count += 1
        except Exception as exc:
            outbox_repo.mark_retryable_failure(
                outbox_event_id=event.outbox_event_id,
                error_message=str(exc),
            )
            retried_count += 1

    return SessionFeedbackProjectionOnceResult(
        claimed_count=claimed_count,
        succeeded_count=succeeded_count,
        failed_count=failed_count,
        retried_count=retried_count,
    )


def mark_session_feedback_seen(
    *,
    session_id: UUID,
    principal: PrincipalContext,
    feedback_repo: SessionFeedbackRepositoryPort,
    now: datetime | None = None,
) -> int:
    owner_user_id = feedback_repo.get_session_owner_user_id(session_id=session_id)
    if owner_user_id is None:
        raise SessionNotFoundErrorSessionFeedback()

    is_owner = owner_user_id == principal.user_id
    is_admin = principal.role == "admin"
    if not (is_owner or is_admin):
        raise ForbiddenErrorSessionFeedback(role=principal.role)

    seen_at = now or datetime.now(timezone.utc)
    return feedback_repo.mark_all_feedback_read(session_id=session_id, seen_at=seen_at)
