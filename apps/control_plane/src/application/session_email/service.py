"""Application service for injecting learner email into a session."""

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from apps.contracts.src.types import TRACE_EVENT_ATTACK_EMAIL_SENT
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.email_classification.ports import (
    EmailMaliciousnessClassifierPort,
)
from apps.control_plane.src.application.email_classification.types import (
    EmailClassificationInput,
)
from apps.control_plane.src.application.runtime.ports import RuntimeClientFactoryPort
from apps.control_plane.src.application.runtime.types import InjectEmailInput
from apps.control_plane.src.application.session_query.service import (
    get_session_metadata,
)
from apps.control_plane.src.application.trace.service import append_trace_event
from apps.control_plane.src.application.trace.types import TraceEvent
from apps.control_plane.src.application.session_email.idempotency import (
    build_malicious_email_objective_idempotency_key,
)
from apps.control_plane.src.application.session_email.mapper import (
    map_attack_email_sent_payload,
)
from apps.control_plane.src.application.common.observability import get_correlation_id
from .ports import SessionEmailDeps


class SessionEmailPolicyError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        retryable: bool,
        status_code: int,
        details: dict[str, object] | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.status_code = status_code
        self.details = details


@dataclass(frozen=True)
class InjectSessionEmailCommand:
    session_id: UUID
    principal: PrincipalContext
    email_from: str
    email_subject: str
    email_body: str
    email_id: str | None
    source: str | None


@dataclass(frozen=True)
class InjectSessionEmailResult:
    session_id: UUID


async def inject_session_email_for_session(
    *,
    command: InjectSessionEmailCommand,
    deps: SessionEmailDeps,
    runtime_client_factory: RuntimeClientFactoryPort,
    email_classifier: EmailMaliciousnessClassifierPort,
) -> InjectSessionEmailResult | None:
    session_metadata = get_session_metadata(
        session_id=command.session_id,
        principal=command.principal,
        repo=deps.metadata_repo,
    )

    if session_metadata is None:
        return None

    if not session_metadata.interactive:
        raise SessionEmailPolicyError(
            code="SESSION_NOT_INTERACTIVE",
            message="Session is not interactive",
            retryable=True,
            status_code=409,
            details={"session_id": str(command.session_id)},
        )

    runtime_binding = deps.runtime_binding_repo.get_by_session_id(
        session_id=command.session_id
    )
    if (
        runtime_binding is None
        or runtime_binding.status != "ready"
        or not runtime_binding.base_url
    ):
        current_status = (
            runtime_binding.status if runtime_binding is not None else "missing"
        )
        raise SessionEmailPolicyError(
            code="RUNTIME_NOT_READY",
            message=f"Runtime not ready (status={current_status})",
            retryable=True,
            status_code=409,
            details={
                "session_id": str(command.session_id),
                "runtime_status": current_status,
            },
        )

    client = runtime_client_factory.create(base_url=runtime_binding.base_url)
    classification = await email_classifier.classify_email(
        input=EmailClassificationInput(
            email_from=command.email_from,
            email_subject=command.email_subject,
            email_body=command.email_body,
        )
    )
    derived_malicious = bool(classification.malicious)
    classifier_provider = classification.provider or "unknown"
    classifier_model = classification.model or "unknown"
    classifier_confidence = (
        classification.confidence if classification.confidence is not None else 0.0
    )
    inject_request = InjectEmailInput(
        session_id=command.session_id,
        email_from=command.email_from,
        email_subject=command.email_subject,
        email_body=command.email_body,
        email_id=command.email_id,
        malicious=derived_malicious,
        urgency_marker=classification.urgency_marker,
        source="learner",
    )

    resolved_email_id = await client.inject_email(input=inject_request)
    email_input = InjectEmailInput(
        session_id=inject_request.session_id,
        email_from=inject_request.email_from,
        email_subject=inject_request.email_subject,
        email_body=inject_request.email_body,
        email_id=resolved_email_id,
        malicious=inject_request.malicious,
        urgency_marker=inject_request.urgency_marker,
        source=inject_request.source,
    )

    attack_email_sent_payload = map_attack_email_sent_payload(
        email_input=email_input,
        derived_malicious=derived_malicious,
        classifier_provider=classifier_provider,
        classifier_model=classifier_model,
        classifier_confidence=classifier_confidence,
        urgency_marker=classification.urgency_marker,
    )

    trace_event = TraceEvent(
        event_id=uuid4(),
        session_id=command.session_id,
        family="learner",
        event_type=TRACE_EVENT_ATTACK_EMAIL_SENT,
        occurred_at=datetime.now(timezone.utc),
        source="inject_session_email_service",
        event_index=deps.trace_repo.get_next_event_index(session_id=command.session_id),
        payload=attack_email_sent_payload,
        trace_version=1,
        correlation_id=UUID(get_correlation_id()),
        request_id=None,
        actor_user_id=command.principal.user_id,
        lab_id=session_metadata.lab_id,
        lab_version_id=session_metadata.lab_version_id,
        lab_difficulty=session_metadata.lab_difficulty,
    )
    append_trace_event(
        trace=trace_event, repo=deps.trace_repo, outbox_repo=deps.outbox_repo
    )

    if (
        session_metadata.lab_id is not None
        and session_metadata.lab_version_id is not None
    ):
        deps.outbox_repo.enqueue_for_evaluator(
            session_id=command.session_id,
            lab_id=session_metadata.lab_id,
            lab_version_id=session_metadata.lab_version_id,
            lab_difficulty=session_metadata.lab_difficulty,
            evaluator_version=1,
            start_event_index=trace_event.event_index,
            end_event_index=trace_event.event_index,
        )

    if (
        derived_malicious
        and session_metadata.lab_id is not None
        and session_metadata.lab_version_id is not None
    ):
        if not deps.objective_status.is_malicious_email_injected_complete(
            session_id=command.session_id
        ):
            objective_idempotency_key = build_malicious_email_objective_idempotency_key(
                session_id=command.session_id,
                email_input=email_input,
                derived_malicious=derived_malicious,
            )
            deps.outbox_repo.enqueue_session_objective_completed(
                session_id=command.session_id,
                lab_id=session_metadata.lab_id,
                lab_version_id=session_metadata.lab_version_id,
                objective_key="malicious_email_injected",
                reason_code="EMAIL_INJECT_ACCEPTED",
                trigger_event_index=trace_event.event_index,
                idempotency_key=objective_idempotency_key,
                source="control_plane",
                evaluator_version=None,
                occurred_at=trace_event.occurred_at,
            )

    deps.tx.commit()
    return InjectSessionEmailResult(session_id=command.session_id)
