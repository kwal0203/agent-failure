from datetime import datetime, timezone
from uuid import uuid4

from apps.contracts.src.schemas import (
    SessionFeedbackCreatedEventPayload,
    SessionFeedbackCreatedOutboxEvent,
)
from apps.evaluator.src.application import service
from apps.evaluator.src.application.rules.contract import (
    REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS,
)
from apps.evaluator.src.application.types import EvaluatorFinding, EvaluatorTaskInput


def _task() -> EvaluatorTaskInput:
    return EvaluatorTaskInput(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        lab_difficulty="easy",
        evaluator_version=1,
        start_event_index=0,
        end_event_index=0,
    )


def _finding(*, trigger_event_index: int | None) -> EvaluatorFinding:
    return EvaluatorFinding(
        result_type="no_effect",
        code="pi.benign_email_injected_no_progress",
        trigger_event_index=trigger_event_index,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="info",
        reason_code=REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS,
        feedback_payload={},
    )


def test_feedback_mapping_keys_are_canonical_reason_code_constants() -> None:
    assert set(service._FEEDBACK_TEMPLATE_BY_REASON_CODE.keys()) == {
        REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS
    }


def test_session_feedback_created_payload_matches_contract_schema_exactly() -> None:
    event = service._build_session_feedback_created_event(
        task=_task(),
        finding=_finding(trigger_event_index=19),
        created_at=datetime.now(timezone.utc),
    )
    assert event is not None

    payload = {
        "session_id": event.session_id,
        "lab_id": event.lab_id,
        "lab_version_id": event.lab_version_id,
        "feedback_key": event.feedback_key,
        "reason_code": event.reason_code,
        "message": event.message,
        "severity": event.severity,
        "trigger_event_index": event.trigger_event_index,
        "created_at": event.created_at,
        "idempotency_key": event.idempotency_key,
    }
    expected_keys = {
        "session_id",
        "lab_id",
        "lab_version_id",
        "feedback_key",
        "reason_code",
        "message",
        "severity",
        "trigger_event_index",
        "created_at",
        "idempotency_key",
    }
    assert set(payload.keys()) == expected_keys

    validated_payload = SessionFeedbackCreatedEventPayload.model_validate(payload)
    assert validated_payload.model_dump().keys() == payload.keys()


def test_session_feedback_created_outbox_event_type_and_nullable_trigger_preserved() -> (
    None
):
    event = service._build_session_feedback_created_event(
        task=_task(),
        finding=_finding(trigger_event_index=None),
        created_at=datetime.now(timezone.utc),
    )
    assert event is not None

    payload = {
        "session_id": event.session_id,
        "lab_id": event.lab_id,
        "lab_version_id": event.lab_version_id,
        "feedback_key": event.feedback_key,
        "reason_code": event.reason_code,
        "message": event.message,
        "severity": event.severity,
        "trigger_event_index": event.trigger_event_index,
        "created_at": event.created_at,
        "idempotency_key": event.idempotency_key,
    }
    assert "trigger_event_index" in payload
    assert payload["trigger_event_index"] is None

    outbox_event = SessionFeedbackCreatedOutboxEvent.model_validate(
        {
            "event_type": "session.feedback.created.v1",
            "aggregate_id": event.session_id,
            "payload": payload,
        }
    )
    assert outbox_event.event_type == "session.feedback.created.v1"
    assert outbox_event.payload.trigger_event_index is None
