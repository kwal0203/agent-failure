from datetime import datetime, timedelta, timezone
from uuid import UUID

from .idempotency import build_hint_unlock_idempotency_key
from .ports import (
    LabHintTemplateReaderPort,
    OutboxSessionHintUnlockedPort,
    SessionHintProjectorPort,
    SessionHintWriterPort,
)
from .types import SessionHintUnlockOnceResult


def initialize_session_hints(
    *,
    session_id: UUID,
    lab_version_id: UUID,
    activated_at: datetime,
    template_reader: LabHintTemplateReaderPort,
    hint_writer: SessionHintWriterPort,
) -> int:
    """
    Materialize hint templates for a session.

    Returns the number of templates processed.
    """
    templates = template_reader.list_hint_templates(lab_version_id=lab_version_id)
    activated_at_utc = (
        activated_at.replace(tzinfo=timezone.utc)
        if activated_at.tzinfo is None
        else activated_at.astimezone(timezone.utc)
    )

    for hint in templates:
        unlock_at = activated_at_utc + timedelta(seconds=hint.offset_seconds)
        hint_writer.upsert_hint(
            session_id=session_id,
            hint_key=hint.hint_key,
            text=hint.text,
            sort_order=hint.sort_order,
            unlock_at=unlock_at,
        )

    return len(templates)


def process_due_session_hints_once(
    *,
    projector: SessionHintProjectorPort,
    outbox: OutboxSessionHintUnlockedPort,
    now: datetime | None = None,
) -> SessionHintUnlockOnceResult:
    ts = now or datetime.now(timezone.utc)
    due_hints = projector.claim_due_pending_hints(now=ts)
    claimed_count = len(due_hints)
    succeeded_count = 0
    skipped_count = 0

    for hint in due_hints:
        changed = projector.mark_unlocked(
            session_id=hint.session_id,
            hint_key=hint.hint_key,
            unlocked_at=ts,
        )
        if not changed:
            skipped_count += 1
            continue

        outbox.enqueue_session_hint_unlocked(
            session_id=hint.session_id,
            hint_key=hint.hint_key,
            text=hint.text,
            sort_order=hint.sort_order,
            unlocked_at=ts,
            idempotency_key=build_hint_unlock_idempotency_key(
                session_id=hint.session_id,
                hint_key=hint.hint_key,
            ),
        )
        succeeded_count += 1

    return SessionHintUnlockOnceResult(
        claimed_count=claimed_count,
        succeeded_count=succeeded_count,
        skipped_count=skipped_count,
    )
