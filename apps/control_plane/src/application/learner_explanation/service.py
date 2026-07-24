from apps.control_plane.src.application.common.errors import (
    DuplicateIdempotencyKeyError,
)
from apps.control_plane.src.application.trace.ports import TraceEventPort
from apps.control_plane.src.application.trace.types import TraceEvent
from apps.control_plane.src.application.trace.service import append_trace_event
from apps.control_plane.src.application.session_lifecycle.ports import Outbox

from .ports import LearnerExplanationPort
from .types import LearnerExplanationInput, LearnerExplanationOutput
from .errors import InvalidLearnerExplanationError

from uuid import uuid4
from datetime import datetime, timezone


def inject_learner_explanation(
    repo: LearnerExplanationPort,
    learner_input: LearnerExplanationInput,
    trace_repo: TraceEventPort,
    outbox: Outbox,
) -> LearnerExplanationOutput:
    explanation = learner_input.explanation.strip()
    if not explanation:
        raise InvalidLearnerExplanationError(code="INVALID_EXPLANATION")

    source = learner_input.source.strip()
    if source != "learner":
        raise InvalidLearnerExplanationError(code="INVALID_SOURCE")

    idempotency_key = learner_input.idempotency_key.strip()
    if not idempotency_key or len(idempotency_key) > 128:
        raise InvalidLearnerExplanationError(code="INVALID_IDEMPOTENCY_KEY")

    normalized = LearnerExplanationInput(
        explanation=explanation,
        session_id=learner_input.session_id,
        lab_id=learner_input.lab_id,
        lab_version_id=learner_input.lab_version_id,
        actor_user_id=learner_input.actor_user_id,
        idempotency_key=idempotency_key,
        source=source,
    )

    existing = repo.get_by_session_and_idempotency_key(
        session_id=normalized.session_id,
        idempotency_key=normalized.idempotency_key,
    )
    if existing is not None:
        return existing

    try:
        result = repo.inject_learner_explanation(input=normalized)
    except DuplicateIdempotencyKeyError:
        existing = repo.get_by_session_and_idempotency_key(
            session_id=normalized.session_id, idempotency_key=normalized.idempotency_key
        )
        if existing is None:
            raise
        return existing

    ts = datetime.now(timezone.utc)
    event_index = trace_repo.get_next_event_index(session_id=normalized.session_id)
    trace_event = TraceEvent(
        event_id=uuid4(),
        session_id=normalized.session_id,
        family="learner",
        event_type="LEARNER_EXPLANATION_SUBMITTED",
        occurred_at=ts,
        source="inject_learner_explanation_service",
        event_index=event_index,
        payload={
            "type": "learner_explanation_submitted",
            "explanation_id": str(result.explanation_id),
            "source": normalized.source,
            "explanation_length": len(normalized.explanation),
        },
        trace_version=1,
        correlation_id=None,
        request_id=None,
        actor_user_id=normalized.actor_user_id,
        lab_id=normalized.lab_id,
        lab_version_id=normalized.lab_version_id,
    )
    append_trace_event(trace=trace_event, repo=trace_repo, outbox_repo=outbox)

    outbox.enqueue_for_evaluator(
        session_id=normalized.session_id,
        lab_id=normalized.lab_id,
        lab_version_id=normalized.lab_version_id,
        evaluator_version=1,
        start_event_index=event_index,
        end_event_index=event_index,
        requested_at=ts,
    )

    return result
