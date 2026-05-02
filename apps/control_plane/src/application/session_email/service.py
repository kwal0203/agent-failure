from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

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
from apps.control_plane.src.infrastructure.persistence.models import (
    SessionObjectiveModel,
)
from apps.control_plane.src.infrastructure.persistence.outbox import SQLAlchemyOutbox
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionMetadataRepository,
    SQLAlchemySessionRuntimeBindingRepository,
    SQLAlchemyTraceEventRepository,
)
from apps.control_plane.src.interfaces.http.helpers import build_trace_event
from apps.control_plane.src.interfaces.http.mappers.session_email_mapper import (
    build_malicious_email_objective_idempotency_key,
    map_attack_email_sent_payload,
)


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
    db: Session,
    runtime_client_factory: RuntimeClientFactoryPort,
    email_classifier: EmailMaliciousnessClassifierPort,
) -> InjectSessionEmailResult | None:
    repo = SQLAlchemySessionMetadataRepository(db=db)
    runtime_binding_repo = SQLAlchemySessionRuntimeBindingRepository(db=db)
    trace_repo = SQLAlchemyTraceEventRepository(db=db)
    outbox_repo = SQLAlchemyOutbox(db=db)

    session_metadata = get_session_metadata(
        session_id=command.session_id,
        principal=command.principal,
        repo=repo,
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

    runtime_binding = runtime_binding_repo.get_by_session_id(
        session_id=command.session_id
    )
    if runtime_binding is None or runtime_binding.status != "ready":
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
    injected_email_id = command.email_id or f"email-{uuid4().hex}"

    email_input = InjectEmailInput(
        session_id=command.session_id,
        email_from=command.email_from,
        email_subject=command.email_subject,
        email_body=command.email_body,
        email_id=injected_email_id,
        malicious=derived_malicious,
        urgency_marker=classification.urgency_marker,
        source="learner",
    )

    await client.inject_email(input=email_input)

    attack_email_sent_payload = map_attack_email_sent_payload(
        email_input=email_input,
        derived_malicious=derived_malicious,
        classifier_provider=classifier_provider,
        classifier_model=classifier_model,
        classifier_confidence=classifier_confidence,
        urgency_marker=classification.urgency_marker,
    )

    trace_event = build_trace_event(
        trace_repo=trace_repo,
        session_id=command.session_id,
        family="learner",
        event_type="ATTACK_EMAIL_SENT",
        source="inject_session_email_service",
        payload=attack_email_sent_payload,
        correlation_id=None,
        request_id=None,
        actor_user_id=command.principal.user_id,
        lab_id=session_metadata.lab_id,
        lab_version_id=session_metadata.lab_version_id,
        lab_difficulty=session_metadata.lab_difficulty,
    )
    append_trace_event(trace=trace_event, repo=trace_repo, outbox_repo=outbox_repo)

    if (
        session_metadata.lab_id is not None
        and session_metadata.lab_version_id is not None
    ):
        outbox_repo.enqueue_for_evaluator(
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
        objective = (
            db.execute(
                select(SessionObjectiveModel).where(
                    SessionObjectiveModel.session_id == command.session_id,
                    SessionObjectiveModel.objective_key == "malicious_email_injected",
                )
            )
            .scalars()
            .one_or_none()
        )
        if objective is None or objective.status != "complete":
            objective_idempotency_key = build_malicious_email_objective_idempotency_key(
                session_id=command.session_id,
                email_input=email_input,
                derived_malicious=derived_malicious,
            )
            outbox_repo.enqueue_session_objective_completed(
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

    db.commit()
    return InjectSessionEmailResult(session_id=command.session_id)
