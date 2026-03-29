from uuid import UUID
from datetime import datetime, timezone

from apps.control_plane.src.application.evaluator_feedback.ports import (
    LearnerFeedbackPublisherPort,
)
from apps.control_plane.src.application.evaluator_feedback.types import (
    LearnerEvaluatorFeedback,
)
from apps.control_plane.src.interfaces.http.session_manager import (
    WebSocketSessionManager,
)
from apps.control_plane.src.interfaces.http.stream_messages import (
    ServerMessageEnvelope,
    LearnerFeedbackItem,
    LearnerFeedbackPayload,
)


class WebSocketLearnerFeedbackPublisher(LearnerFeedbackPublisherPort):
    def __init__(self, gateway: WebSocketSessionManager) -> None:
        self._gateway = gateway

    async def publish_session_feedback(
        self, session_id: UUID, feedback: tuple[LearnerEvaluatorFeedback, ...]
    ) -> None:
        feedback_items: list[LearnerFeedbackItem] = []
        for item in feedback:
            feedback_items.append(
                LearnerFeedbackItem(
                    status=item.status,
                    reason_code=item.reason_code,
                    evidence_snippet=item.evidence_snippet,
                )
            )

        message = ServerMessageEnvelope(
            type="LEARNER_FEEDBACK",
            session_id=session_id,
            timestamp=datetime.now(timezone.utc),
            payload=LearnerFeedbackPayload(feedback=feedback_items),
            event_index=None,
            request_id=None,
            correlation_id=None,
            final=True,
        )
        await self._gateway.broadcast(session_id=session_id, message=message)
