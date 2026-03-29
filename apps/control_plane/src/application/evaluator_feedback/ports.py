from typing import Protocol
from uuid import UUID
from datetime import datetime

from .types import (
    EvaluatorPersistedResult,
    PendingLearnerFeedbackPublishEvent,
    LearnerEvaluatorFeedback,
)


class EvaluatorPort(Protocol):
    def list_results_for_session(
        self, session_id: UUID
    ) -> tuple[EvaluatorPersistedResult, ...]: ...


class OutboxLearnerFeedbackPublishPort(Protocol):
    def claim_pending_feedback_publish(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingLearnerFeedbackPublishEvent]: ...

    def mark_processed(
        self, *, outbox_event_id: UUID, processed_at: datetime | None = None
    ) -> None: ...

    def mark_retryable_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        backoff_seconds: int = 15,
        failed_at: datetime | None = None,
    ) -> None: ...

    def mark_terminal_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        failed_at: datetime | None = None,
    ) -> None: ...


class LearnerFeedbackPublisherPort(Protocol):
    async def publish_session_feedback(
        self, session_id: UUID, feedback: tuple[LearnerEvaluatorFeedback, ...]
    ) -> None: ...
