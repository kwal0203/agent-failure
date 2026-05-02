import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from apps.contracts.src.schemas import ApiErrorEnvelope, EmailArtifact
from apps.control_plane.src.application.common.errors import (
    DuplicateIdempotencyKeyError,
    ForbiddenError,
)
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.email_classification.ports import (
    EmailMaliciousnessClassifierPort,
)
from apps.control_plane.src.application.evaluator_feedback.service import (
    get_session_evaluator_feedback,
)
from apps.control_plane.src.application.learner_explanation.errors import (
    InvalidLearnerExplanationError,
)
from apps.control_plane.src.application.runtime.errors import RuntimeClientError
from apps.control_plane.src.application.runtime.ports import RuntimeClientFactoryPort
from apps.control_plane.src.application.session_email.service import (
    InjectSessionEmailCommand,
    SessionEmailPolicyError,
    inject_session_email_for_session,
)
from apps.control_plane.src.application.session_explanation_submission.service import (
    SessionExplanationPolicyError,
    SubmitLearnerExplanationCommand,
    submit_learner_explanation,
)
from apps.control_plane.src.application.session_create.ports import (
    AdmissionPolicy,
    CreateSessionUnitOfWork,
)
from apps.control_plane.src.application.session_create.service import create_session
from apps.control_plane.src.application.session_feedback.service import (
    mark_session_feedback_seen,
)
from apps.control_plane.src.application.session_hints.service import (
    mark_session_hints_seen,
)
from apps.control_plane.src.application.session_lifecycle.errors import SessionNotFound
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
    project_learner_visible_events,
)
from apps.control_plane.src.domain.session_lifecycle.state_machine import Trigger
from apps.control_plane.src.infrastructure.persistence.db import (
    SessionFactory,
    get_db_session,
)
from apps.control_plane.src.infrastructure.persistence.session_feedback_repository import (
    SQLAlchemySessionFeedbackRepository,
)
from apps.control_plane.src.infrastructure.persistence.session_hints_repository import (
    SQLAlchemySessionHintSeenRepository,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemyEvaluatorRepository,
    SQLAlchemySessionMetadataRepository,
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
from apps.control_plane.src.interfaces.http.translators.create_session import (
    translate_create_session_error,
)
from apps.control_plane.src.interfaces.http.translators.session_actions import (
    translate_mark_feedback_seen_error,
    translate_mark_hints_seen_error,
    translate_stop_session_error,
)
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
    except Exception as exc:
        try:
            return translate_create_session_error(exc)
        except TypeError:
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

    except SessionNotFound:
        return session_not_found(str(session_id))
    except Exception as exc:
        response = translate_stop_session_error(exc, session_id=session_id)
        if response.status_code == 500:
            logger.exception("stop session failed for session=%s", str(session_id))
        return response


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
    except Exception as exc:
        db.rollback()
        response = translate_mark_hints_seen_error(exc, session_id=session_id)
        if response.status_code == 500:
            logger.exception("mark hints seen failed")
        return response


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
    except Exception as exc:
        db.rollback()
        response = translate_mark_feedback_seen_error(exc, session_id=session_id)
        if response.status_code == 500:
            logger.exception("mark feedback seen failed")
        return response


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
        result = await inject_session_email_for_session(
            command=InjectSessionEmailCommand(
                session_id=session_id,
                principal=principal,
                email_from=request.email_from,
                email_subject=request.email_subject,
                email_body=request.email_body,
                email_id=request.email_id,
                source=request.source,
            ),
            db=db,
            runtime_client_factory=runtime_client_factory,
            email_classifier=email_classifier,
        )
        if result is None:
            return session_not_found(str(session_id))
        return InjectSessionEmailResponse(session_id=result.session_id)

    except ForbiddenErrorSessionQuery as exc:
        return forbidden(exc.message, exc.details)
    except SessionEmailPolicyError as exc:
        db.rollback()
        return api_error(
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            status_code=exc.status_code,
            details=exc.details,
        )

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

    try:
        result = submit_learner_explanation(
            command=SubmitLearnerExplanationCommand(
                session_id=session_id,
                principal=principal,
                explanation=request.explanation,
                idempotency_key=key,
            ),
            db=db,
        )
        if result is None:
            return session_not_found(str(session_id))
        return LearnerExplanationResponse(
            session_id=session_id,
            explanation_id=result.explanation_id,
            accepted=True,
        )
    except SessionExplanationPolicyError as exc:
        return api_error(
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            status_code=exc.status_code,
            details=exc.details,
        )
    except InvalidLearnerExplanationError as exc:
        return api_error(
            code=exc.code,
            message=exc.message,
            retryable=False,
            status_code=400,
            details=exc.details,
        )
    except ForbiddenErrorSessionQuery as exc:
        return forbidden(exc.message, exc.details)
    except ValidationError:
        return api_error(
            code="SESSION_METADATA_INVALID",
            message="Invalid lab difficulty on session_metadata",
            retryable=False,
            status_code=500,
            details={"session_id": str(session_id)},
        )
    except DuplicateIdempotencyKeyError as exc:
        return api_error(
            code=exc.code,
            message=exc.message,
            retryable=False,
            status_code=500,
            details=exc.details,
        )
    except Exception:
        logger.exception("learner explanation endpoint failed")
        return api_error(
            code="INTERNAL_SERVER_ERROR",
            message="Unknown error in explanation endpoint",
            retryable=False,
            status_code=500,
            details={"session_id": str(session_id)},
        )
