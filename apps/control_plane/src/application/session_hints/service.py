from datetime import datetime, timedelta, timezone
from uuid import UUID

from .ports import LabHintTemplateReaderPort, SessionHintWriterPort


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
