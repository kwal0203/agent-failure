import hashlib
import logging
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.contracts.src.schemas import ApiErrorEnvelope, EmailArtifact
from apps.control_plane.src.application.common.errors import (
    DuplicateIdempotencyKeyError,
    ForbiddenError,
)
from apps.control_plane.src.application.common.schemas import LabDifficultyParser
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.email_classification.ports import (
    EmailMaliciousnessClassifierPort,
)
from apps.control_plane.src.application.email_classification.types import (
    EmailClassificationInput,
)
from apps.control_plane.src.application.evaluator_feedback.service import (
    get_session_evaluator_feedback,
)
from apps.control_plane.src.application.learner_explanation.errors import (
    InvalidLearnerExplanationError,
)
from apps.control_plane.src.application.learner_explanation.service import (
    inject_learner_explanation,
)
from apps.control_plane.src.application.learner_explanation.types import (
    LearnerExplanationInput,
)
from apps.control_plane.src.application.runtime.errors import RuntimeClientError
from apps.control_plane.src.application.runtime.ports import RuntimeClientFactoryPort
from apps.control_plane.src.application.runtime.types import InjectEmailInput
from apps.control_plane.src.application.session_create.errors import (
    AdmissionDecisionError,
    DegradedModeRestrictionError,
    InvalidIdempotencyKeyError,
    InvalidLabDifficulty,
    LabNotAvailableError,
    QuotaExceededError,
    RateLimitedError,
)
from apps.control_plane.src.application.session_create.ports import (
    AdmissionPolicy,
    CreateSessionUnitOfWork,
)
from apps.control_plane.src.application.session_create.service import create_session
from apps.control_plane.src.application.session_feedback.errors import (
    ForbiddenErrorSessionFeedback,
    SessionNotFoundErrorSessionFeedback,
)
from apps.control_plane.src.application.session_feedback.service import (
    mark_session_feedback_seen,
)
from apps.control_plane.src.application.session_hints.errors import (
    ForbiddenErrorSessionHints,
    SessionNotFoundErrorSessionHints,
)
from apps.control_plane.src.application.session_hints.service import (
    mark_session_hints_seen,
)
from apps.control_plane.src.application.session_lifecycle.errors import (
    InvalidTransition,
    SessionNotFound,
)
from apps.control_plane.src.application.session_lifecycle.service import (
    transition_session,
)
from apps.control_plane.src.application.session_query.errors import (
    ForbiddenErrorSessionQuery,
)
from apps.control_plane.src.application.session_query.ports import (
    SessionMetadataRepository,
)
from apps.control_plane.src.application.session_query.service import (
    get_session_metadata,
)
from apps.control_plane.src.application.trace.service import (
    append_trace_event,
    project_learner_visible_events,
)
from apps.control_plane.src.domain.session_lifecycle.state_machine import Trigger
from apps.control_plane.src.infrastructure.persistence.db import (
    SessionFactory,
    get_db_session,
)
from apps.control_plane.src.infrastructure.persistence.learner_explanation_repository import (
    LearnerExplanationRepository,
)
from apps.control_plane.src.infrastructure.persistence.models import (
    SessionObjectiveModel,
)
from apps.control_plane.src.infrastructure.persistence.outbox import SQLAlchemyOutbox
from apps.control_plane.src.infrastructure.persistence.session_feedback_repository import (
    SQLAlchemySessionFeedbackRepository,
)
from apps.control_plane.src.infrastructure.persistence.session_hints_repository import (
    SQLAlchemySessionHintSeenRepository,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemyEvaluatorRepository,
    SQLAlchemySessionMetadataRepository,
    SQLAlchemySessionRuntimeBindingRepository,
    SQLAlchemyTraceEventRepository,
)
from apps.control_plane.src.infrastructure.persistence.unit_of_work import (
    SQLAlchemyUnitOfWork,
)
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.dependencies import (
    get_admission_policy,
    get_create_session_uow,
    get_email_maliciousness_classifier,
    get_runtime_client_factory,
    get_session_metadata_repository,
)
from apps.control_plane.src.interfaces.http.errors import (
    api_error,
    forbidden,
    internal_error,
    session_not_found,
)
from apps.control_plane.src.interfaces.http.helpers import build_trace_event
from apps.control_plane.src.interfaces.http.mappers.session_mapper import (
    map_evaluator_feedback_response,
    map_session_trace_response,
)
from apps.control_plane.src.interfaces.http.schemas import (
    CreateSessionRequest,
    CreateSessionResponse,
    GetFeedbackResponse,
    GetSessionTraceResponse,
    InjectSessionEmailResponse,
    LearnerExplanationRequest,
    LearnerExplanationResponse,
    MarkSessionFeedbackSeenResponse,
    MarkSessionHintsSeenResponse,
    SessionResponse,
    StopSessionResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _exception_log_helper(
    content: str,
    event: str,
    reason: str,
    request: CreateSessionRequest,
    principal: PrincipalContext,
) -> None:
    logger.warning(
        str(content),
        extra={
            "event": str(event),
            "reason": str(reason),
            "lab_id": str(request.lab_id),
            "lab_difficulty": str(request.lab_difficulty),
            "user_id": str(principal.user_id),
        },
    )


@router.post(
    "/api/v1/sessions",
    response_model=CreateSessionResponse,
    status_code=202,
    responses={
        400: {"model": ApiErrorEnvelope},
        401: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        404: {"model": ApiErrorEnvelope},
        429: {"model": ApiErrorEnvelope},
        500: {"model": ApiErrorEnvelope},
        503: {"model": ApiErrorEnvelope},
    },
)
def create_session_endpoint(
    request: CreateSessionRequest,
    principal: PrincipalContext = Depends(get_current_principal),
    admission_policy: AdmissionPolicy = Depends(get_admission_policy),
    uow: CreateSessionUnitOfWork = Depends(get_create_session_uow),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> CreateSessionResponse | JSONResponse | None:
    key = idempotency_key.strip()
    if not key or len(key) > 128:
        return api_error(
            code="INVALID_IDEMPOTENCY_KEY",
            message="Valid Idempotency-Key header is required",
            retryable=False,
            status_code=400,
        )

    application_principal = PrincipalContext(
        user_id=principal.user_id, role=principal.role
    )

    try:
        result = create_session(
            principal=application_principal,
            admission_policy=admission_policy,
            lab_id=request.lab_id,
            lab_difficulty=request.lab_difficulty,
            idempotency_key=key,
            uow=uow,
        )
        session = SessionResponse(
            id=result.session_id,
            lab_id=result.lab_id,
            lab_version_id=result.lab_version_id,
            lab_difficulty=result.lab_difficulty,
            state=result.state,
            resume_mode=result.resume_mode,
            created_at=result.created_at,
        )

        logger.info(
            "create session succeeded",
            extra={
                "event": "create_session_succeeded",
                "session_id": str(result.session_id),
                "lab_id": str(result.lab_id),
                "lab_version_id": str(result.lab_version_id)
                if result.lab_version_id is not None
                else None,
                "lab_difficulty": result.lab_difficulty,
                "user_id": str(application_principal.user_id),
            },
        )

        return CreateSessionResponse(session=session)
    except LabNotAvailableError as exc:
        _exception_log_helper(
            "lab_not_available",
            "create_session_denied",
            "LAB_NOT_AVAILABLE",
            request,
            principal,
        )
        return api_error(
            code="LAB_NOT_AVAILABLE",
            message=exc.message,
            retryable=False,
            status_code=404,
            details=exc.details,
        )
    except QuotaExceededError as exc:
        _exception_log_helper(
            "quota_exceeded",
            "create_session_denied",
            "QUOTA_EXCEEDED",
            request,
            principal,
        )
        return api_error(
            code="QUOTA_EXCEEDED",
            message=exc.message,
            retryable=False,
            status_code=429,
            details=exc.details,
        )
    except RateLimitedError as exc:
        _exception_log_helper(
            "rate_limited", "create_session_denied", "RATE_LIMITED", request, principal
        )
        return api_error(
            code="RATE_LIMITED",
            message=exc.message,
            retryable=False,
            status_code=429,
            details=exc.details,
        )
    except DegradedModeRestrictionError as exc:
        _exception_log_helper(
            "degraded_mode_restriction",
            "create_session_denied",
            "DEGRADED_MODE_RESTRICTION",
            request,
            principal,
        )
        return api_error(
            code="DEGRADED_MODE_RESTRICTION",
            message=exc.message,
            retryable=False,
            status_code=503,
            details=exc.details,
        )
    except InvalidIdempotencyKeyError as exc:
        _exception_log_helper(
            "invalid_idempotency_key",
            "create_session_denied",
            "INVALID_IDEMPOTENCY_KEY",
            request,
            principal,
        )
        return api_error(
            code="INVALID_IDEMPOTENCY_KEY",
            message=exc.message,
            retryable=False,
            status_code=400,
            details=exc.details,
        )
    except ForbiddenError as exc:
        _exception_log_helper(
            "forbidden", "create_session_denied", "FORBIDDEN", request, principal
        )
        return forbidden(exc.message, exc.details)
    except AdmissionDecisionError as exc:
        _exception_log_helper(
            "admission_denied",
            "create_session_denied",
            "ADMISSION_DENIED",
            request,
            principal,
        )
        return api_error(
            code="ADMISSION_DENIED",
            message=exc.message,
            retryable=False,
            status_code=400,
            details=exc.details,
        )
    except InvalidLabDifficulty as exc:
        _exception_log_helper(
            "invalid_lab_difficulty",
            "create_session_denied",
            "INVALID_LAB_DIFFICULTY",
            request,
            principal,
        )
        return api_error(
            code="INVALID_LAB_DIFFICULTY",
            message=exc.message,
            retryable=False,
            status_code=400,
            details=exc.details,
        )
    except Exception:
        safe_idempo = f"{key[:8]}..." if key else None
        logger.exception(
            "create session endpoint failed",
            extra={
                "event": "create_session_failed",
                "lab_id": str(request.lab_id),
                "lab_difficulty": request.lab_difficulty,
                "user_id": str(application_principal.user_id),
                "idempotency_key_prefix": safe_idempo,
            },
        )

        return internal_error()


@router.post(
    "/api/v1/sessions/{session_id}/stop",
    status_code=202,
    response_model=StopSessionResponse,
    responses={
        401: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        404: {"model": ApiErrorEnvelope},
        409: {"model": ApiErrorEnvelope},
        500: {"model": ApiErrorEnvelope},
    },
)
def stop_session_endpoint(
    session_id: UUID,
    principal: PrincipalContext = Depends(get_current_principal),
    metadata_repo: SessionMetadataRepository = Depends(get_session_metadata_repository),
) -> StopSessionResponse | JSONResponse:
    try:
        session_metadata = get_session_metadata(
            session_id=session_id,
            principal=principal,
            repo=metadata_repo,
        )
        if session_metadata is None:
            return session_not_found(str(session_id))

        if session_metadata.state in {"COMPLETED", "FAILED", "EXPIRED", "CANCELLED"}:
            return StopSessionResponse(
                session_id=session_id,
                accepted=True,
                state=session_metadata.state,
            )

        uow = SQLAlchemyUnitOfWork(session_factory=SessionFactory)
        transition_session(
            session_id=session_id,
            trigger=Trigger.ADMIN_CANCELLED,
            actor="admin",
            metadata={
                "reason_code": "USER_REQUESTED_STOP",
                "requested_by_user_id": str(principal.user_id),
                "requested_via": "session_ui",
            },
            idempotency_key=f"stop-session:{session_id}:{principal.user_id}",
            uow=uow,
        )

        return StopSessionResponse(
            session_id=session_id,
            accepted=True,
            state="CANCELLED",
        )

    except ForbiddenErrorSessionQuery as exc:
        return forbidden(exc.message, exc.details)
    except SessionNotFound:
        return session_not_found(str(session_id))
    except InvalidTransition as exc:
        return api_error(
            code="INVALID_SESSION_STATE",
            message="Session cannot be stopped from the current state",
            retryable=False,
            status_code=409,
            details={
                "session_id": str(session_id),
                "current_state": exc.current_state.value,
                "trigger": exc.trigger.value,
            },
        )
    except Exception:
        logger.exception("stop session failed for session=%s", str(session_id))
        return internal_error(
            "Unexpected server error", details={"session_id": str(session_id)}
        )


@router.post(
    "/api/v1/sessions/{session_id}/hints/mark-seen",
    response_model=MarkSessionHintsSeenResponse,
    responses={
        401: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        404: {"model": ApiErrorEnvelope},
    },
)
def mark_hints_seen_endpoint(
    session_id: UUID,
    principal: PrincipalContext = Depends(get_current_principal),
    db: Session = Depends(get_db_session),
) -> MarkSessionHintsSeenResponse | JSONResponse:
    seen_repo = SQLAlchemySessionHintSeenRepository(db=db)
    try:
        updated_count = mark_session_hints_seen(
            session_id=session_id,
            principal=principal,
            seen_repo=seen_repo,
        )
        db.commit()
        return MarkSessionHintsSeenResponse(
            session_id=session_id,
            updated_count=updated_count,
        )
    except ForbiddenErrorSessionHints as exc:
        db.rollback()
        return forbidden(exc.message, exc.details)
    except SessionNotFoundErrorSessionHints:
        db.rollback()
        return api_error(
            code="SESSION_NOT_FOUND",
            message="Session not found",
            retryable=False,
            status_code=404,
            details={"session_id": str(session_id), "exists": False},
        )
    except Exception:
        db.rollback()
        logger.exception("mark hints seen failed")
        return internal_error(
            "Unexpected server error", details={"session_id": str(session_id)}
        )


@router.post(
    "/api/v1/sessions/{session_id}/feedback/mark-seen",
    response_model=MarkSessionFeedbackSeenResponse,
    responses={
        401: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        404: {"model": ApiErrorEnvelope},
    },
)
def mark_feedback_seen_endpoint(
    session_id: UUID,
    principal: PrincipalContext = Depends(get_current_principal),
    db: Session = Depends(get_db_session),
) -> MarkSessionFeedbackSeenResponse | JSONResponse:
    feedback_repo = SQLAlchemySessionFeedbackRepository(db=db)
    try:
        updated_count = mark_session_feedback_seen(
            session_id=session_id,
            principal=principal,
            feedback_repo=feedback_repo,
        )
        db.commit()
        return MarkSessionFeedbackSeenResponse(
            session_id=session_id,
            updated_count=updated_count,
        )
    except ForbiddenErrorSessionFeedback as exc:
        db.rollback()
        return forbidden(exc.message, exc.details)
    except SessionNotFoundErrorSessionFeedback:
        db.rollback()
        return api_error(
            code="SESSION_NOT_FOUND",
            message="Session not found",
            retryable=False,
            status_code=404,
            details={"session_id": str(session_id), "exists": False},
        )
    except Exception:
        db.rollback()
        logger.exception("mark feedback seen failed")
        return internal_error(
            "Unexpected server error", details={"session_id": str(session_id)}
        )


@router.get(
    "/api/v1/sessions/{session_id}/evaluator-feedback",
    response_model=GetFeedbackResponse,
    responses={
        401: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        500: {"model": ApiErrorEnvelope},
    },
)
def evaluator_feedback(
    session_id: UUID,
    principal: PrincipalContext = Depends(get_current_principal),
    db: Session = Depends(get_db_session),
) -> GetFeedbackResponse | JSONResponse:
    repo = SQLAlchemyEvaluatorRepository(db=db)

    try:
        evaluator_feedback_item = get_session_evaluator_feedback(
            principal=principal, session_id=session_id, repo=repo
        )
        return map_evaluator_feedback_response(evaluator_feedback_item)

    except ForbiddenError as exc:
        return forbidden(exc.message, exc.details)

    except Exception:
        logger.exception(
            "get evaluator feedback endpoint failed for session=%s", str(session_id)
        )
        return internal_error()


@router.get(
    "/api/v1/sessions/{session_id}/trace",
    response_model=GetSessionTraceResponse,
    responses={
        401: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        404: {"model": ApiErrorEnvelope},
        500: {"model": ApiErrorEnvelope},
    },
)
def get_session_trace(
    session_id: UUID,
    principal: PrincipalContext = Depends(get_current_principal),
    db: Session = Depends(get_db_session),
) -> GetSessionTraceResponse | JSONResponse:

    repo = SQLAlchemyTraceEventRepository(db=db)
    metadata_repo = SQLAlchemySessionMetadataRepository(db=db)

    try:
        session_metadata = get_session_metadata(
            session_id=session_id,
            principal=principal,
            repo=metadata_repo,
        )
        if session_metadata is None:
            return session_not_found(str(session_id))

        events = repo.list_trace_events_for_session(session_id=session_id)
        learner_events = project_learner_visible_events(events=events)

        return map_session_trace_response(learner_events)

    except ForbiddenErrorSessionQuery as exc:
        return forbidden(exc.message, exc.details)
    except Exception:
        logger.exception(
            "get session trace endpoint failed for session=%s", str(session_id)
        )
        return internal_error()


@router.post(
    "/api/v1/sessions/{session_id}/inbox/email",
    status_code=202,
    response_model=InjectSessionEmailResponse,
    responses={
        401: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        404: {"model": ApiErrorEnvelope},
        409: {"model": ApiErrorEnvelope},
        502: {"model": ApiErrorEnvelope},
    },
)
async def inject_session_email(
    request: EmailArtifact,
    session_id: UUID,
    principal: PrincipalContext = Depends(get_current_principal),
    runtime_client_factory: RuntimeClientFactoryPort = Depends(
        get_runtime_client_factory
    ),
    email_classifier: EmailMaliciousnessClassifierPort = Depends(
        get_email_maliciousness_classifier
    ),
    db: Session = Depends(get_db_session),
) -> InjectSessionEmailResponse | JSONResponse:
    try:
        repo = SQLAlchemySessionMetadataRepository(db=db)
        runtime_binding_repo = SQLAlchemySessionRuntimeBindingRepository(db=db)
        trace_repo = SQLAlchemyTraceEventRepository(db=db)
        outbox_repo = SQLAlchemyOutbox(db=db)

        session_metadata = get_session_metadata(
            session_id=session_id, principal=principal, repo=repo
        )

        if session_metadata is None:
            return session_not_found(str(session_id))

        if not session_metadata.interactive:
            return api_error(
                code="SESSION_NOT_INTERACTIVE",
                message="Session is not interactive",
                retryable=True,
                status_code=409,
                details={"session_id": str(session_id)},
            )

        runtime_binding = runtime_binding_repo.get_by_session_id(session_id=session_id)
        if runtime_binding is None or runtime_binding.status != "ready":
            current_status = (
                runtime_binding.status if runtime_binding is not None else "missing"
            )

            logger.warning(
                "runtime binding not ready",
                extra={
                    "event": "runtime_binding_not_ready",
                    "session_id": str(session_id),
                    "status": current_status,
                    "base_url": runtime_binding.base_url
                    if runtime_binding is not None
                    else None,
                    "lab_difficulty": session_metadata.lab_difficulty,
                },
            )
            return api_error(
                code="RUNTIME_NOT_READY",
                message=f"Runtime not ready (status={current_status})",
                retryable=True,
                status_code=409,
                details={
                    "session_id": str(session_id),
                    "runtime_status": current_status,
                },
            )

        client = runtime_client_factory.create(base_url=runtime_binding.base_url)
        classification = await email_classifier.classify_email(
            input=EmailClassificationInput(
                email_from=request.email_from,
                email_subject=request.email_subject,
                email_body=request.email_body,
            )
        )
        derived_malicious = bool(classification.malicious)
        injected_email_id = request.email_id or f"email-{uuid4().hex}"

        email_input = InjectEmailInput(
            session_id=session_id,
            email_from=request.email_from,
            email_subject=request.email_subject,
            email_body=request.email_body,
            email_id=injected_email_id,
            malicious=derived_malicious,
            urgency_marker=classification.urgency_marker,
            source=request.source,
        )

        await client.inject_email(input=email_input)

        attack_email_sent_payload: dict[str, object] = {
            "type": "attack_email_sent",
            "email_id": email_input.email_id,
            "email_from": email_input.email_from,
            "subject": email_input.email_subject,
            "malicious_marker": derived_malicious,
            "urgency_marker": classification.urgency_marker,
            "classifier_provider": classification.provider,
            "classifier_model": classification.model,
            "classifier_confidence": classification.confidence,
        }

        trace_event = build_trace_event(
            trace_repo=trace_repo,
            session_id=session_id,
            family="learner",
            event_type="ATTACK_EMAIL_SENT",
            source="inject_session_email_service",
            payload=attack_email_sent_payload,
            correlation_id=None,
            request_id=None,
            actor_user_id=principal.user_id,
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
                session_id=session_id,
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
                        SessionObjectiveModel.session_id == session_id,
                        SessionObjectiveModel.objective_key
                        == "malicious_email_injected",
                    )
                )
                .scalars()
                .one_or_none()
            )
            if objective is None or objective.status != "complete":
                fingerprint = hashlib.sha256(
                    "|".join(
                        [
                            str(session_id),
                            email_input.email_from.strip().lower(),
                            email_input.email_subject.strip(),
                            email_input.email_body.strip(),
                            str(derived_malicious),
                            (email_input.source or "learner").strip().lower(),
                            (email_input.email_id or "").strip(),
                        ]
                    ).encode("utf-8")
                ).hexdigest()
                objective_idempotency_key = (
                    f"objective:{session_id}:malicious_email_injected:{fingerprint}"
                )

                outbox_repo.enqueue_session_objective_completed(
                    session_id=session_id,
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
        return InjectSessionEmailResponse(session_id=session_id)

    except ForbiddenErrorSessionQuery as exc:
        return forbidden(exc.message, exc.details)

    except RuntimeClientError as exc:
        db.rollback()
        return api_error(
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            status_code=502,
            details={"session_id": str(session_id)},
        )
    except RuntimeError as exc:
        db.rollback()
        return api_error(
            code="EMAIL_CLASSIFICATION_FAILED",
            message=str(exc),
            retryable=True,
            status_code=502,
            details={"session_id": str(session_id)},
        )
    except Exception:
        db.rollback()
        logger.exception("inject session email failed")
        return internal_error(
            "Unexpected server error", details={"session_id": str(session_id)}
        )


@router.post(
    "/api/v1/sessions/{session_id}/explanation",
    status_code=202,
    response_model=LearnerExplanationResponse,
    responses={
        400: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        404: {"model": ApiErrorEnvelope},
        409: {"model": ApiErrorEnvelope},
        500: {"model": ApiErrorEnvelope},
    },
)
def learner_explanation(
    session_id: UUID,
    request: LearnerExplanationRequest,
    principal: PrincipalContext = Depends(get_current_principal),
    db: Session = Depends(get_db_session),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> LearnerExplanationResponse | JSONResponse:
    key = idempotency_key.strip()
    if not key or len(key) > 128:
        logger.warning(
            "invalid learner explanation idempotency key",
            extra={
                "event": "learner_explanation_invalid_idempotency_key",
                "session_id": str(session_id),
                "lab_id": None,
                "lab_difficulty": None,
                "user_id": str(principal.user_id),
            },
        )
        return api_error(
            code="INVALID_IDEMPOTENCY_KEY",
            message="Valid Idempotency-Key header is required",
            retryable=False,
            status_code=400,
        )

    log_lab_id: str | None = None
    log_lab_difficulty: str | None = None

    try:
        session_metadata_repo = SQLAlchemySessionMetadataRepository(db=db)
        session_metadata = get_session_metadata(
            session_id=session_id,
            principal=principal,
            repo=session_metadata_repo,
        )

        if session_metadata is None:
            logger.warning(
                "learner explanation session not found",
                extra={
                    "event": "learner_explanation_session_not_found",
                    "session_id": str(session_id),
                    "lab_id": None,
                    "lab_difficulty": None,
                    "user_id": str(principal.user_id),
                },
            )
            return session_not_found(str(session_id))

        log_lab_id = str(session_metadata.lab_id) if session_metadata.lab_id else None
        log_lab_difficulty = (
            None
            if not session_metadata.lab_difficulty
            else str(session_metadata.lab_difficulty)
        )

        if session_metadata.state != "COMPLETED":
            logger.warning(
                "learner explanation rejected due to session state",
                extra={
                    "event": "learner_explanation_session_not_ready",
                    "session_id": str(session_id),
                    "lab_id": log_lab_id,
                    "lab_difficulty": log_lab_difficulty,
                    "user_id": str(principal.user_id),
                },
            )
            return api_error(
                code="SESSION_NOT_READY",
                message="Explanations can only be submitted after lab completion.",
                retryable=False,
                status_code=409,
                details={
                    "session_id": str(session_id),
                    "state": session_metadata.state,
                    "required_state": "COMPLETED",
                },
            )

        lab_id = session_metadata.lab_id
        lab_version_id = session_metadata.lab_version_id

        if lab_id is None or lab_version_id is None:
            logger.error(
                "learner explanation session metadata incomplete",
                extra={
                    "event": "learner_explanation_session_metadata_incomplete",
                    "session_id": str(session_id),
                    "lab_id": log_lab_id,
                    "lab_difficulty": log_lab_difficulty,
                    "user_id": str(principal.user_id),
                },
            )
            return api_error(
                code="SESSION_METADATA_INCOMPLETE",
                message="Session is missing lab metadata required for explanation submission.",
                retryable=False,
                status_code=500,
                details={"session_id": str(session_id)},
            )

        parsed = LabDifficultyParser.model_validate(
            {"lab_difficulty": session_metadata.lab_difficulty}
        )
        explanation_artifact = LearnerExplanationInput(
            explanation=request.explanation,
            session_id=session_metadata.id,
            lab_id=lab_id,
            lab_version_id=lab_version_id,
            lab_difficulty=parsed.lab_difficulty,
            actor_user_id=principal.user_id,
            idempotency_key=key,
            source="learner",
        )

        learner_explanation_repo = LearnerExplanationRepository(db=db)
        trace_repo = SQLAlchemyTraceEventRepository(db=db)
        outbox = SQLAlchemyOutbox(db=db)
        result = inject_learner_explanation(
            repo=learner_explanation_repo,
            learner_input=explanation_artifact,
            trace_repo=trace_repo,
            outbox=outbox,
        )

        logger.info(
            "learner explanation accepted",
            extra={
                "event": "learner_explanation_submitted",
                "session_id": str(session_id),
                "lab_id": str(lab_id),
                "lab_difficulty": parsed.lab_difficulty,
                "user_id": str(principal.user_id),
            },
        )
        return LearnerExplanationResponse(
            session_id=session_id, explanation_id=result.explanation_id, accepted=True
        )

    except InvalidLearnerExplanationError as exc:
        logger.warning(
            "learner explanation validation failed",
            extra={
                "event": "learner_explanation_invalid_request",
                "session_id": str(session_id),
                "lab_id": log_lab_id,
                "lab_difficulty": log_lab_difficulty,
                "user_id": str(principal.user_id),
            },
        )
        return api_error(
            code=exc.code,
            message=exc.message,
            retryable=False,
            status_code=400,
            details=exc.details,
        )
    except ForbiddenErrorSessionQuery as exc:
        logger.warning(
            "learner explanation forbidden",
            extra={
                "event": "learner_explanation_forbidden",
                "session_id": str(session_id),
                "lab_id": log_lab_id,
                "lab_difficulty": log_lab_difficulty,
                "user_id": str(principal.user_id),
            },
        )
        return forbidden(exc.message, exc.details)
    except ValidationError:
        logger.exception(
            "learner explanation metadata validation failed",
            extra={
                "event": "learner_explanation_session_metadata_invalid",
                "session_id": str(session_id),
                "lab_id": log_lab_id,
                "lab_difficulty": log_lab_difficulty,
                "user_id": str(principal.user_id),
            },
        )
        return api_error(
            code="SESSION_METADATA_INVALID",
            message="Invalid lab difficulty on session_metadata",
            retryable=False,
            status_code=500,
            details={"session_id": str(session_id)},
        )
    except DuplicateIdempotencyKeyError as exc:
        logger.exception(
            "learner explanation idempotency replay failed",
            extra={
                "event": "learner_explanation_idempotency_replay_failed",
                "session_id": str(session_id),
                "lab_id": log_lab_id,
                "lab_difficulty": log_lab_difficulty,
                "user_id": str(principal.user_id),
            },
        )
        return api_error(
            code=exc.code,
            message=exc.message,
            retryable=False,
            status_code=500,
            details=exc.details,
        )
    except Exception:
        logger.exception(
            "learner explanation endpoint failed",
            extra={
                "event": "learner_explanation_internal_error",
                "session_id": str(session_id),
                "lab_id": log_lab_id,
                "lab_difficulty": log_lab_difficulty,
                "user_id": str(principal.user_id),
            },
        )
        return api_error(
            code="INTERNAL_SERVER_ERROR",
            message="Unknown error in explanation endpoint",
            retryable=False,
            status_code=500,
            details={"session_id": str(session_id)},
        )
