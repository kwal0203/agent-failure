from typing import Any

from sqlalchemy.sql.elements import ColumnElement

from .models import SessionFeedbackModel


def session_feedback_ordering() -> tuple[ColumnElement[Any], ...]:
    return (
        SessionFeedbackModel.created_at.asc(),
        SessionFeedbackModel.trigger_event_index.asc().nullslast(),
        SessionFeedbackModel.id.asc(),
    )
