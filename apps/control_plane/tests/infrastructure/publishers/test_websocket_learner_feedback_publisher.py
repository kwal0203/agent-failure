from datetime import UTC, datetime
import asyncio
from uuid import UUID, uuid4

import pytest

from apps.control_plane.src.application.evaluator_feedback.types import (
    LearnerEvaluatorFeedback,
)
from apps.control_plane.src.infrastructure.publishers.websocket_learner_feedback_publisher import (
    WebSocketLearnerFeedbackPublisher,
)
from apps.control_plane.src.interfaces.http.session_manager import (
    WebSocketSessionManager,
)
from apps.control_plane.src.interfaces.http.stream_messages import ServerMessageEnvelope


def test_websocket_learner_feedback_publisher_emits_expected_message_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gateway = WebSocketSessionManager()
    calls: list[tuple[UUID, ServerMessageEnvelope]] = []

    async def _fake_broadcast(session_id: UUID, message: ServerMessageEnvelope) -> None:
        calls.append((session_id, message))

    monkeypatch.setattr(gateway, "broadcast", _fake_broadcast)

    publisher = WebSocketLearnerFeedbackPublisher(gateway=gateway)
    session_id = uuid4()
    feedback = (
        LearnerEvaluatorFeedback(
            status="learned",
            reason_code="PI_SECRET_EXFILTRATION_DETECTED",
            evidence_snippet="FLAG{abc123}",
        ),
        LearnerEvaluatorFeedback(
            status="progress",
            reason_code="PI_ATTACK_ATTEMPT_BLOCKED",
            evidence_snippet="Attack attempt blocked by model_policy (POLICY_DENIED)",
        ),
    )

    asyncio.run(
        publisher.publish_session_feedback(session_id=session_id, feedback=feedback)
    )

    assert len(calls) == 1
    broadcast_session_id, message = calls[0]
    assert broadcast_session_id == session_id
    assert message.type == "LEARNER_FEEDBACK"
    assert message.session_id == session_id
    assert isinstance(message.timestamp, datetime)
    assert message.timestamp.tzinfo == UTC
    assert message.final is True

    payload = message.payload.model_dump(mode="json")
    assert payload == {
        "feedback": [
            {
                "status": "learned",
                "reason_code": "PI_SECRET_EXFILTRATION_DETECTED",
                "evidence_snippet": "FLAG{abc123}",
            },
            {
                "status": "progress",
                "reason_code": "PI_ATTACK_ATTEMPT_BLOCKED",
                "evidence_snippet": "Attack attempt blocked by model_policy (POLICY_DENIED)",
            },
        ]
    }
