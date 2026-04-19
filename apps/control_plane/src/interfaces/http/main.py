from fastapi import FastAPI, Depends, Request, Header, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import hashlib
from sqlalchemy.orm import Session
from sqlalchemy import select
from uuid import UUID, uuid4
from datetime import datetime, timezone
from .schemas import (
    GetSessionMetadataResponse,
    SessionMetadataResponse,
    SessionResponse,
    CreateSessionResponse,
    CreateSessionRequest,
    GetLabsResponse,
    LabCatalogItemResponse,
    LabCapabilitiesResponse,
    EvaluatorFeedbackResponse,
    GetFeedbackResponse,
    SessionTraceEvent,
    GetSessionTraceResponse,
    InjectSessionEmailResponse,
    LearnerExplanationRequest,
    LearnerExplanationResponse,
    SessionProgressChipResponse,
    SessionHintResponse,
)
from apps.control_plane.src.infrastructure.persistence.lab_repository import (
    SQLAlchemyLabRepository,
)
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionMetadataRepository,
)
from apps.control_plane.src.infrastructure.persistence.worker_heartbeat_repository import (
    SQLAlchemyWorkerHeartbeatRepository,
)
from apps.control_plane.src.infrastructure.persistence.outbox import SQLAlchemyOutbox
from apps.control_plane.src.application.session_query.service import (
    get_session_metadata,
)
from apps.control_plane.src.application.session_query.errors import (
    ForbiddenErrorSessionQuery,
)
from apps.control_plane.src.application.session_create.ports import (
    AdmissionPolicy,
    CreateSessionUnitOfWork,
)
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.common.schemas import LabDifficultyParser
from apps.control_plane.src.application.common.errors import (
    ForbiddenError,
    DuplicateIdempotencyKeyError,
)
from apps.control_plane.src.application.session_create.service import create_session
from apps.control_plane.src.application.session_create.errors import (
    LabNotAvailableError,
    QuotaExceededError,
    RateLimitedError,
    DegradedModeRestrictionError,
    InvalidIdempotencyKeyError,
    AdmissionDecisionError,
    InvalidLabDifficulty,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemyTraceEventRepository,
    SQLAlchemyEvaluatorRepository,
    SQLAlchemySessionRuntimeBindingRepository,
)
from apps.control_plane.src.infrastructure.persistence.models import (
    SessionObjectiveModel,
)
from apps.control_plane.src.interfaces.runtime.learner_feedback_worker import (
    run_forever,
)
from apps.control_plane.src.application.trace.types import TraceEvent
from apps.control_plane.src.application.trace.service import append_trace_event
from apps.control_plane.src.application.lab_catalog.service import (
    get_labs_for_principal,
)
from apps.control_plane.src.application.evaluator_feedback.service import (
    get_session_evaluator_feedback,
)
from apps.control_plane.src.application.trace.service import (
    project_learner_visible_events,
)
from apps.control_plane.src.application.runtime.ports import RuntimeClientFactoryPort
from apps.control_plane.src.application.runtime.types import (
    RunTurnInput,
    InjectEmailInput,
)
from apps.control_plane.src.application.runtime.errors import RuntimeClientError
from apps.control_plane.src.application.learner_explanation.service import (
    inject_learner_explanation,
)
from apps.control_plane.src.application.learner_explanation.types import (
    LearnerExplanationInput,
)
from apps.control_plane.src.application.learner_explanation.errors import (
    InvalidLearnerExplanationError,
)
from apps.control_plane.src.infrastructure.persistence.learner_explanation_repository import (
    LearnerExplanationRepository,
)
from apps.contracts.src.schemas import EmailArtifact, ApiErrorEnvelope
from .dependencies import (
    get_admission_policy,
    get_create_session_uow,
    get_session_metadata_repository,
    get_runtime_client_factory,
)
from .auth import (
    UnauthenticatedError,
    get_current_principal,
    get_current_principal_ws,
)
from .stream_messages import (
    UserPromptMessage,
)
from .session_manager import WebSocketSessionManager
from .message_builders import (
    build_policy_denial_message,
    build_agent_text_chunk_message,
    build_session_status_message,
    build_trace_event_message,
    build_system_error_message,
)
from .helpers import (
    build_trace_event,
    build_model_turn_failed_payload,
    build_api_error_response,
)

import logging
import asyncio
import contextlib


PROVISIONING_STALL_SESSION_AGE_SECONDS = 360
PROVISIONING_STALL_HEARTBEAT_AGE_SECONDS = 360

logger = logging.getLogger(__name__)

ws_manager: WebSocketSessionManager = WebSocketSessionManager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.learner_feedback_task = asyncio.create_task(
        run_forever(session_manager=ws_manager)
    )
    try:
        yield
    finally:
        task = app.state.learner_feedback_task
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(UnauthenticatedError)
async def handle_unauthenticated(
    request: Request, exc: UnauthenticatedError
) -> JSONResponse:
    return build_api_error_response(
        "UNAUTHENTICATED", "Missing or invalid bearer token", False, 401
    )


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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


@app.get(
    "/api/v1/sessions/{session_id}",
    response_model=GetSessionMetadataResponse,
    responses={
        401: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        404: {"model": ApiErrorEnvelope},
    },
)
def get_metadata(
    session_id: UUID,
    principal: PrincipalContext = Depends(get_current_principal),
    db: Session = Depends(get_db_session),
) -> GetSessionMetadataResponse | JSONResponse:
    repo = SQLAlchemySessionMetadataRepository(db=db)
    heartbeat_repo = SQLAlchemyWorkerHeartbeatRepository()

    try:
        session_metadata = get_session_metadata(
            session_id=session_id,
            principal=principal,
            repo=repo,
        )
        if session_metadata is None:
            return build_api_error_response(
                "SESSION_NOT_FOUND",
                "Session not found",
                False,
                404,
                {"session_id": str(session_id)},
            )

        stalled = False
        if session_metadata.state == "PROVISIONING":
            try:
                hb = heartbeat_repo.read_heartbeat(worker_name="provisioning_worker")

                created_at = _as_utc(session_metadata.created_at)
                last_tick_at = _as_utc(hb.last_tick_at) if hb else None
                now = datetime.now(timezone.utc)

                if created_at:
                    session_age_s = (now - created_at).total_seconds()
                    hb_age_s = (
                        (now - last_tick_at).total_seconds() if last_tick_at else None
                    )
                    stalled = (
                        session_age_s >= PROVISIONING_STALL_SESSION_AGE_SECONDS
                        and (
                            hb_age_s is None
                            or hb_age_s >= PROVISIONING_STALL_HEARTBEAT_AGE_SECONDS
                        )
                    )

            except Exception:
                logger.warning("heartbeat read failed in get_metadata", exc_info=True)

        progress_chips: list[SessionProgressChipResponse] = []
        for progress_item in session_metadata.progress_chips:
            progress_chips.append(
                SessionProgressChipResponse(
                    objective_key=progress_item.objective_key,
                    label=progress_item.label,
                    status=progress_item.status,
                    completed_at=progress_item.completed_at,
                    updated_at=progress_item.updated_at,
                )
            )
        hints: list[SessionHintResponse] = []
        for hint_item in session_metadata.hints:
            hints.append(
                SessionHintResponse(
                    hint_key=hint_item.hint_key,
                    text=hint_item.text,
                    sort_order=hint_item.sort_order,
                    status=hint_item.status,
                    unlock_at=hint_item.unlock_at,
                    unlocked_at=hint_item.unlocked_at,
                    seen_at=hint_item.seen_at,
                )
            )

        http_obj = SessionMetadataResponse(
            id=session_metadata.id,
            lab_id=session_metadata.lab_id,
            lab_version_id=session_metadata.lab_version_id,
            lab_difficulty=session_metadata.lab_difficulty,
            state=session_metadata.state,
            runtime_substate=session_metadata.runtime_substate,
            resume_mode=session_metadata.resume_mode,
            # TODO(P2-EA follow-up): Keep legacy field name for now to avoid
            # response churn; normalize to failure_reason_code in a cleanup pass.
            last_transition_reason=session_metadata.last_transition_reason,
            interactive=session_metadata.interactive,
            created_at=session_metadata.created_at,
            started_at=session_metadata.started_at,
            ended_at=session_metadata.ended_at,
            provisioning_stalled=stalled,
            provisioning_stall_reason_code="SESSION_PROVISIONING_STALLED"
            if stalled
            else None,
            progress_chips=progress_chips,
            hints=hints,
            unread_hint_count=session_metadata.unread_hint_count,
        )
        return GetSessionMetadataResponse(session=http_obj)

    except ForbiddenErrorSessionQuery as exc:
        return build_api_error_response(
            "FORBIDDEN", exc.message, False, 403, exc.details
        )


@app.post(
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
        return build_api_error_response(
            "INVALID_IDEMPOTENCY_KEY",
            "Valid Idempotency-Key header is required",
            False,
            400,
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
        return build_api_error_response(
            "LAB_NOT_AVAILABLE", exc.message, False, 404, exc.details
        )
    except QuotaExceededError as exc:
        _exception_log_helper(
            "quota_exceeded",
            "create_session_denied",
            "QUOTA_EXCEEDED",
            request,
            principal,
        )
        return build_api_error_response(
            "QUOTA_EXCEEDED", exc.message, False, 429, exc.details
        )
    except RateLimitedError as exc:
        _exception_log_helper(
            "rate_limited", "create_session_denied", "RATE_LIMITED", request, principal
        )
        return build_api_error_response(
            "RATE_LIMITED", exc.message, False, 429, exc.details
        )
    except DegradedModeRestrictionError as exc:
        _exception_log_helper(
            "degraded_mode_restriction",
            "create_session_denied",
            "DEGRADED_MODE_RESTRICTION",
            request,
            principal,
        )
        return build_api_error_response(
            "DEGRADED_MODE_RESTRICTION", exc.message, False, 503, exc.details
        )
    except InvalidIdempotencyKeyError as exc:
        _exception_log_helper(
            "invalid_idempotency_key",
            "create_session_denied",
            "INVALID_IDEMPOTENCY_KEY",
            request,
            principal,
        )
        return build_api_error_response(
            "INVALID_IDEMPOTENCY_KEY", exc.message, False, 400, exc.details
        )
    except ForbiddenError as exc:
        _exception_log_helper(
            "forbidden", "create_session_denied", "FORBIDDEN", request, principal
        )
        return build_api_error_response(
            "FORBIDDEN", exc.message, False, 403, exc.details
        )
    except AdmissionDecisionError as exc:
        _exception_log_helper(
            "admission_denied",
            "create_session_denied",
            "ADMISSION_DENIED",
            request,
            principal,
        )
        return build_api_error_response(
            "ADMISSION_DENIED", exc.message, False, 400, exc.details
        )
    except InvalidLabDifficulty as exc:
        _exception_log_helper(
            "invalid_lab_difficulty",
            "create_session_denied",
            "INVALID_LAB_DIFFICULTY",
            request,
            principal,
        )
        return build_api_error_response(
            "INVALID_LAB_DIFFICULTY", exc.message, False, 400, exc.details
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

        return build_api_error_response(
            "INTERNAL_ERROR", "unexpected server error", False, 500, None
        )


async def handle_user_prompt(
    websocket: WebSocket,
    session_id: UUID,
    principal: PrincipalContext,
    prompt_content: str,
    db: Session,
    runtime_client_factory: RuntimeClientFactoryPort,
):
    repo = SQLAlchemySessionMetadataRepository(db=db)
    outbox_repo = SQLAlchemyOutbox(db=db)
    runtime_binding_repo = SQLAlchemySessionRuntimeBindingRepository(db=db)

    if not ws_manager.try_begin_turn(session_id=session_id):
        await ws_manager.send_to(
            websocket,
            build_policy_denial_message(
                session_id, "TURN_IN_PROGRESS", "Turn in progress"
            ),
        )
        return

    try:
        metadata = get_session_metadata(
            session_id=session_id,
            principal=principal,
            repo=repo,
        )
        if metadata is None:
            await ws_manager.send_to(
                websocket,
                build_policy_denial_message(
                    session_id, "SESSION_NOT_FOUND", "Session not found"
                ),
            )
            return

        if not metadata.interactive:
            await ws_manager.send_to(
                websocket,
                build_policy_denial_message(
                    session_id, "SESSION_NOT_INTERACTIVE", "Session not interactive"
                ),
            )
            return

        if metadata.lab_id is None or metadata.lab_version_id is None:
            await ws_manager.send_to(
                websocket,
                build_policy_denial_message(
                    session_id,
                    "SESSION_MISSING_CONTEXT",
                    "Session is missing lab context (lab id or lab version id)",
                ),
            )
            return

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
                    "lab_difficulty": metadata.lab_difficulty,
                },
            )
            await ws_manager.send_to(
                websocket,
                build_policy_denial_message(
                    session_id=session_id,
                    reason_code="RUNTIME_BINDING_NOT_READY",
                    message=f"Runtime is not ready: (status={current_status})",
                ),
            )
            return

        runtime_client = runtime_client_factory.create(
            base_url=runtime_binding.base_url
        )

        # TODO(P1-E6 follow-up): This writes learner trace directly via DB adapter
        # in the websocket handler. Move to UoW-backed trace write path so turn
        # handling and trace persistence share a clear transactional boundary.
        # learner trace
        trace_repo = SQLAlchemyTraceEventRepository(db=db)
        trace_event = TraceEvent(
            event_id=uuid4(),
            session_id=session_id,
            family="learner",
            event_type="USER_PROMPT_SUBMITTED",
            occurred_at=datetime.now(timezone.utc),
            source="session_stream_service",
            event_index=trace_repo.get_next_event_index(session_id=session_id),
            payload={
                # TODO(P1-E6/P1-E7 follow-up): Prompt content is persisted in full
                # for MVP evaluator/replay visibility. Revisit policy to decide
                # whether this should be redacted/summarized/hashed by default.
                "content": prompt_content,
                "role": "user",
                "channel": "websocket",
                "message_type": "USER_PROMPT",
            },
            trace_version=1,
            correlation_id=None,
            request_id=None,
            actor_user_id=principal.user_id,
            lab_id=metadata.lab_id,
            lab_version_id=metadata.lab_version_id,
            lab_difficulty=metadata.lab_difficulty,
        )
        append_trace_event(trace=trace_event, repo=trace_repo, outbox_repo=outbox_repo)

        try:
            await ws_manager.send_to(
                websocket,
                build_trace_event_message(session_id, "TURN_STARTED", "Turn started"),
            )

            await ws_manager.send_to(
                websocket,
                build_trace_event_message(
                    session_id, "MODEL_REQUEST_STARTED", "Model request started"
                ),
            )

            trace_event_model_started = build_trace_event(
                trace_repo=trace_repo,
                session_id=session_id,
                family="model",
                event_type="MODEL_TURN_STARTED",
                source="session_stream_service",
                payload={
                    "provider": "openrouter",
                    "message_type": "USER_PROMPT",
                    "prompt_chars": len(prompt_content),
                },
                actor_user_id=principal.user_id,
                lab_id=metadata.lab_id,
                lab_version_id=metadata.lab_version_id,
                lab_difficulty=metadata.lab_difficulty,
            )

            append_trace_event(
                trace=trace_event_model_started,
                repo=trace_repo,
                outbox_repo=outbox_repo,
            )

            turn_id = uuid4()
            turn = RunTurnInput(
                session_id=metadata.id,
                lab_id=metadata.lab_id,
                lab_version_id=metadata.lab_version_id,
                turn_id=turn_id,
                prompt=prompt_content,
                idempotency_key=f"turn:{metadata.id}:{turn_id}",
            )

            turn_start = datetime.now(timezone.utc)
            first_chunk_emitted = False
            chunks_emitted = 0
            full_response_text_parts: list[str] = []
            completed = False
            async for event in runtime_client.run_turn_stream(input=turn):
                if event.type == "turn_started":
                    continue

                if event.type == "text_chunk":
                    try:
                        await asyncio.wait_for(
                            ws_manager.send_to(
                                websocket,
                                build_agent_text_chunk_message(
                                    session_id=session_id,
                                    chunk=event.content,
                                    final=event.final,
                                ),
                            ),
                            timeout=10.0,
                        )

                    except asyncio.TimeoutError:
                        logger.warning(
                            "turn stream send timeout",
                            extra={
                                "event": "turn_failed_mid_stream",
                                "session_id": str(session_id),
                                "reason_code": "TURN_FAILED_MID_STREAM",
                                "retryable": True,
                                "first_chunk_emitted": first_chunk_emitted,
                                "chunks_emitted": chunks_emitted,
                                "upstream_error_type": "WS_SEND_TIMEOUT",
                                "lab_difficulty": metadata.lab_difficulty,
                            },
                        )
                        await ws_manager.send_to(
                            websocket,
                            build_system_error_message(
                                session_id=session_id,
                                error_code="TURN_FAILED_MID_STREAM",
                                message="The response was interrupted. You can retry to continue.",
                            ),
                        )

                        mid_stream_failure_payload = build_model_turn_failed_payload(
                            error_code="TURN_FAILED_MID_STREAM",
                            phase="mid_stream",
                            turn_start=turn_start,
                            chunks_emitted=chunks_emitted,
                        )
                        trace_event_model_failed = build_trace_event(
                            trace_repo=trace_repo,
                            session_id=session_id,
                            family="model",
                            event_type="MODEL_TURN_FAILED",
                            source="session_stream_service",
                            payload=mid_stream_failure_payload,
                            actor_user_id=principal.user_id,
                            lab_id=metadata.lab_id,
                            lab_version_id=metadata.lab_version_id,
                            lab_difficulty=metadata.lab_difficulty,
                        )
                        append_trace_event(
                            trace=trace_event_model_failed,
                            repo=trace_repo,
                            outbox_repo=outbox_repo,
                        )

                        db.commit()
                        return

                    except WebSocketDisconnect:
                        logger.info(
                            "turn stream client disconnected",
                            extra={
                                "event": "turn_stream_disconnected",
                                "session_id": str(session_id),
                                "chunks_emitted": chunks_emitted,
                                "lab_difficulty": metadata.lab_difficulty,
                            },
                        )
                        db.commit()
                        return

                    except Exception:
                        logger.exception(
                            "turn stream send failed",
                            extra={
                                "event": "turn_failed_mid_stream",
                                "session_id": str(session_id),
                                "reason_code": "TURN_FAILED_MID_STREAM",
                                "retryable": True,
                                "first_chunk_emitted": first_chunk_emitted,
                                "chunks_emitted": chunks_emitted,
                                "lab_difficulty": metadata.lab_difficulty,
                            },
                        )
                        await ws_manager.send_to(
                            websocket,
                            build_system_error_message(
                                session_id,
                                "TURN_FAILED_MID_STREAM",
                                "The response was interrupted. You can retry to continue.",
                            ),
                        )

                        trace_event_model_failed = build_trace_event(
                            trace_repo=trace_repo,
                            session_id=session_id,
                            family="model",
                            event_type="MODEL_TURN_FAILED",
                            source="session_stream_service",
                            payload={
                                "provider": "openrouter",
                                "error_code": "TURN_FAILED_MID_STREAM",
                                "retryable": True,
                                "phase": "mid_stream",
                                "duration_ms": int(
                                    (
                                        datetime.now(timezone.utc) - turn_start
                                    ).total_seconds()
                                    * 1000
                                ),
                                "chunks_emitted": chunks_emitted,
                            },
                            actor_user_id=principal.user_id,
                            lab_id=metadata.lab_id,
                            lab_version_id=metadata.lab_version_id,
                            lab_difficulty=metadata.lab_difficulty,
                        )
                        append_trace_event(
                            trace=trace_event_model_failed,
                            repo=trace_repo,
                            outbox_repo=outbox_repo,
                        )

                        db.commit()
                        return

                    first_chunk_emitted = True
                    chunks_emitted += 1
                    full_response_text_parts.append(event.content)
                    continue

                if event.type == "turn_failed":
                    reason_code = (
                        "TURN_FAILED_MID_STREAM"
                        if first_chunk_emitted
                        else "TURN_FAILED_BEFORE_FIRST_CHUNK"
                    )
                    phase = (
                        "mid_stream" if first_chunk_emitted else "before_first_chunk"
                    )
                    log_message = (
                        "turn failed mid stream"
                        if first_chunk_emitted
                        else "turn failed before first chunk"
                    )
                    logger.warning(
                        log_message,
                        extra={
                            "event": reason_code.lower(),
                            "session_id": str(session_id),
                            "reason_code": reason_code,
                            "retryable": getattr(event, "retryable", True),
                            "first_chunk_emitted": first_chunk_emitted,
                            "time_to_failure_ms": int(
                                (
                                    datetime.now(timezone.utc) - turn_start
                                ).total_seconds()
                                * 1000
                            ),
                            "lab_difficulty": metadata.lab_difficulty,
                        },
                    )

                    default_message = (
                        "The response was interrupted. You can retry to continue."
                        if first_chunk_emitted
                        else "The assistant failed before responding. Please resend your prompt."
                    )
                    await ws_manager.send_to(
                        websocket,
                        build_system_error_message(
                            session_id=session_id,
                            error_code=reason_code,
                            message=getattr(event, "message", default_message),
                        ),
                    )

                    turn_failed_payload = build_model_turn_failed_payload(
                        error_code=reason_code,
                        phase=phase,
                        turn_start=turn_start,
                        chunks_emitted=chunks_emitted,
                    )

                    trace_event_model_failed = build_trace_event(
                        trace_repo=trace_repo,
                        session_id=session_id,
                        family="model",
                        event_type="MODEL_TURN_FAILED",
                        source="session_stream_service",
                        payload=turn_failed_payload,
                        actor_user_id=principal.user_id,
                        lab_id=metadata.lab_id,
                        lab_version_id=metadata.lab_version_id,
                        lab_difficulty=metadata.lab_difficulty,
                    )

                    append_trace_event(
                        trace=trace_event_model_failed,
                        repo=trace_repo,
                        outbox_repo=outbox_repo,
                    )

                    db.commit()
                    return

                if event.type == "attack_email_sent":
                    attack_email_sent_payload: dict[str, object] = {
                        "type": event.type,
                        "email_id": event.email_id,
                        "recipient": event.recipient,
                        "subject": event.subject,
                    }

                    trace_event = build_trace_event(
                        trace_repo=trace_repo,
                        session_id=session_id,
                        family="runtime",
                        event_type="ATTACK_EMAIL_SENT",
                        source="session_stream_service",
                        payload=attack_email_sent_payload,
                        actor_user_id=principal.user_id,
                        lab_id=metadata.lab_id,
                        lab_version_id=metadata.lab_version_id,
                        lab_difficulty=metadata.lab_difficulty,
                    )

                    append_trace_event(
                        trace=trace_event, repo=trace_repo, outbox_repo=outbox_repo
                    )

                    continue

                if event.type == "inbox_listed":
                    inbox_listed_payload: dict[str, object] = {
                        "type": event.type,
                        "message_count": event.message_count,
                    }

                    trace_event = build_trace_event(
                        trace_repo=trace_repo,
                        session_id=session_id,
                        family="runtime",
                        event_type="INBOX_LISTED",
                        source="session_stream_service",
                        payload=inbox_listed_payload,
                        actor_user_id=principal.user_id,
                        lab_id=metadata.lab_id,
                        lab_version_id=metadata.lab_version_id,
                        lab_difficulty=metadata.lab_difficulty,
                    )

                    append_trace_event(
                        trace=trace_event, repo=trace_repo, outbox_repo=outbox_repo
                    )

                    continue

                if event.type == "email_read":
                    email_read_payload: dict[str, object] = {
                        "type": event.type,
                        "email_id": event.email_id,
                        "subject": event.subject,
                    }

                    trace_event = build_trace_event(
                        trace_repo=trace_repo,
                        session_id=session_id,
                        family="runtime",
                        event_type="EMAIL_READ",
                        source="session_stream_service",
                        payload=email_read_payload,
                        actor_user_id=principal.user_id,
                        lab_id=metadata.lab_id,
                        lab_version_id=metadata.lab_version_id,
                        lab_difficulty=metadata.lab_difficulty,
                    )

                    append_trace_event(
                        trace=trace_event, repo=trace_repo, outbox_repo=outbox_repo
                    )

                    continue

                if event.type == "malicious_email_read":
                    malicious_email_read_payload: dict[str, object] = {
                        "type": event.type,
                        "email_id": event.email_id,
                        "subject": event.subject,
                        "malicious_marker": event.malicious_marker,
                    }

                    trace_event = build_trace_event(
                        trace_repo=trace_repo,
                        session_id=session_id,
                        family="runtime",
                        event_type="MALICIOUS_EMAIL_READ",
                        source="session_stream_service",
                        payload=malicious_email_read_payload,
                        actor_user_id=principal.user_id,
                        lab_id=metadata.lab_id,
                        lab_version_id=metadata.lab_version_id,
                        lab_difficulty=metadata.lab_difficulty,
                    )

                    append_trace_event(
                        trace=trace_event, repo=trace_repo, outbox_repo=outbox_repo
                    )

                    continue

                if event.type == "token_disclosure_attempted":
                    token_disclosure_attempted_payload: dict[str, object] = {
                        "type": event.type,
                        "channel": event.channel,
                        "target": event.target,
                    }

                    trace_event = build_trace_event(
                        trace_repo=trace_repo,
                        session_id=session_id,
                        family="runtime",
                        event_type="TOKEN_DISCLOSURE_ATTEMPTED",
                        source="session_stream_service",
                        payload=token_disclosure_attempted_payload,
                        actor_user_id=principal.user_id,
                        lab_id=metadata.lab_id,
                        lab_version_id=metadata.lab_version_id,
                        lab_difficulty=metadata.lab_difficulty,
                    )

                    append_trace_event(
                        trace=trace_event, repo=trace_repo, outbox_repo=outbox_repo
                    )

                    continue

                if event.type == "token_disclosed":
                    token_disclosed_payload: dict[str, object] = {
                        "type": event.type,
                        "channel": event.channel,
                        "token_kind": event.token_kind,
                    }

                    trace_event = build_trace_event(
                        trace_repo=trace_repo,
                        session_id=session_id,
                        family="runtime",
                        event_type="TOKEN_DISCLOSED",
                        source="session_stream_service",
                        payload=token_disclosed_payload,
                        actor_user_id=principal.user_id,
                        lab_id=metadata.lab_id,
                        lab_version_id=metadata.lab_version_id,
                        lab_difficulty=metadata.lab_difficulty,
                    )

                    append_trace_event(
                        trace=trace_event, repo=trace_repo, outbox_repo=outbox_repo
                    )

                    continue

                if event.type == "turn_completed":
                    completed = True
                    break

            if not completed:
                raise RuntimeClientError(
                    code="RUNTIME_STREAM_INCOMPLETE",
                    message="Runtime stream ended without terminal event",
                    retryable=True,
                )

            trace_event_model_completed = build_trace_event(
                trace_repo=trace_repo,
                session_id=session_id,
                family="model",
                event_type="MODEL_TURN_COMPLETED",
                source="session_stream_service",
                payload={
                    "status": "succeeded",
                    "chunks_emitted": chunks_emitted,
                    "duration_ms": int(
                        (datetime.now(timezone.utc) - turn_start).total_seconds() * 1000
                    ),
                    "first_chunk_emitted": first_chunk_emitted,
                    "content": "".join(full_response_text_parts),
                },
                actor_user_id=principal.user_id,
                lab_id=metadata.lab_id,
                lab_version_id=metadata.lab_version_id,
                lab_difficulty=metadata.lab_difficulty,
            )

            append_trace_event(
                trace=trace_event_model_completed,
                repo=trace_repo,
                outbox_repo=outbox_repo,
            )

            db.commit()

        except RuntimeClientError as exc:
            db.rollback()
            logger.warning(
                "runtime stream failed",
                extra={
                    "event": "runtime_stream_failed",
                    "session_id": str(session_id),
                    "error_code": exc.code,
                    "retryable": exc.retryable,
                    "lab_difficulty": metadata.lab_difficulty,
                },
            )

            await ws_manager.send_to(
                websocket,
                build_system_error_message(
                    session_id=session_id,
                    error_code=exc.code,
                    message=exc.message,
                ),
            )

            return

        except Exception:
            db.rollback()
            logger.exception(f"session prompt handling failed session_id={session_id}")
            await ws_manager.send_to(
                websocket,
                build_system_error_message(
                    session_id, "INTERNAL_ERROR", "Unexpected server error"
                ),
            )
            return

    finally:
        ws_manager.end_turn(session_id=session_id)


@app.websocket("/api/v1/sessions/{session_id}/stream")
async def session_stream_ws(
    websocket: WebSocket,
    session_id: UUID,
    repo: SQLAlchemySessionMetadataRepository = Depends(
        get_session_metadata_repository
    ),
    db: Session = Depends(get_db_session),
    runtime_client_factory: RuntimeClientFactoryPort = Depends(
        get_runtime_client_factory
    ),
):
    # - Authz rules:
    #   - missing/invalid auth => deny.
    #   - non-owner/non-admin => deny.
    try:
        principal = get_current_principal_ws(websocket=websocket)
    except UnauthenticatedError:
        await websocket.close(code=1008, reason="unauthenticated")
        logger.warning(f"session stream denied unauthenticated session_id={session_id}")
        return

    # - owner/admin => allow.
    # - Query session metadata using existing query path (get_session_metadata + repo).
    try:
        metadata = get_session_metadata(
            session_id=session_id,
            principal=principal,
            repo=repo,
        )
    except ForbiddenErrorSessionQuery:
        await websocket.close(code=1008, reason="forbidden")
        logger.warning(
            f"session stream denied forbidden session_id={session_id}, user_id={str(principal.user_id)}, role={principal.role}"
        )
        return

    if metadata is None:
        await websocket.close(code=1008, reason="session not found")
        return

    # if metadata.runtime_substate is None:
    #     await websocket.close(code=1008, reason="session runtime substate not found")
    #     return

    # - On allow: accept, register with manager, send initial SESSION_STATUS.
    await ws_manager.connect(session_id=session_id, websocket=websocket)
    logger.info(
        f"session stream connect session_id={session_id}, user_id={str(principal.user_id)}, role={principal.role}"
    )
    try:
        await ws_manager.send_to(
            websocket,
            build_session_status_message(
                session_id,
                metadata.state,
                metadata.runtime_substate,
                metadata.interactive,
            ),
        )
        while True:
            incoming = await websocket.receive_json()

            try:
                prompt_msg = UserPromptMessage.model_validate(incoming)
            except Exception:
                await ws_manager.send_to(
                    websocket,
                    build_policy_denial_message(
                        session_id, "INVALID_MESSAGE", "Invalid websocket message shape"
                    ),
                )
                continue

            if prompt_msg.type != "USER_PROMPT":
                continue

            if prompt_msg.session_id != session_id:
                await ws_manager.send_to(
                    websocket,
                    build_policy_denial_message(
                        session_id,
                        "SESSION_ID_MISMATCH",
                        "Message session_id does not match stream session_id",
                    ),
                )
                continue

            await handle_user_prompt(
                websocket=websocket,
                session_id=session_id,
                principal=principal,
                prompt_content=prompt_msg.payload.content,
                db=db,
                runtime_client_factory=runtime_client_factory,
            )

    except WebSocketDisconnect:
        pass
    finally:
        # - In finally: manager disconnect + log disconnect.
        ws_manager.disconnect(session_id=session_id, websocket=websocket)
        logger.info(
            f"session stream disconnect session_id={session_id}, user_id={str(principal.user_id)}, role={principal.role}"
        )


@app.get(
    "/api/v1/labs",
    response_model=GetLabsResponse,
    status_code=200,
    responses={401: {"model": ApiErrorEnvelope}, 403: {"model": ApiErrorEnvelope}},
)
def get_labs(
    principal: PrincipalContext = Depends(get_current_principal),
    db: Session = Depends(get_db_session),
) -> GetLabsResponse | JSONResponse:
    lab_repo = SQLAlchemyLabRepository(db=db)

    try:
        labs_for_principal = get_labs_for_principal(
            principal=principal, lab_repo=lab_repo
        ).labs

        result: list[LabCatalogItemResponse] = []
        for lab in labs_for_principal:
            result.append(
                LabCatalogItemResponse(
                    id=lab.lab_id,
                    slug=lab.slug,
                    name=lab.name,
                    summary=lab.summary,
                    capabilities=LabCapabilitiesResponse(
                        supports_resume=lab.capabilities.supports_resume,
                        supports_uploads=lab.capabilities.supports_uploads,
                    ),
                )
            )
        return GetLabsResponse(labs=result)

    except ForbiddenError as exc:
        return build_api_error_response(
            code="FORBIDDEN",
            message=exc.message,
            retryable=False,
            status_code=403,
            details=exc.details,
        )
    # except UnauthenticatedError as exc:
    #     return build_api_error_response(code="UNAUTHENTICATED", message=exc.message, retryable=False, status_code=401, details=exc.details)
    except Exception:
        logger.exception(
            "get labs endpoint failed user_id=%s role=%s",
            str(principal.user_id),
            principal.role,
        )
        return build_api_error_response(
            "INTERNAL_ERROR", "unexpected server error", False, 500, None
        )


@app.get(
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
        evaluator_feedback = get_session_evaluator_feedback(
            principal=principal, session_id=session_id, repo=repo
        )
        tmp: list[EvaluatorFeedbackResponse] = []
        for feedback in evaluator_feedback:
            tmp.append(
                EvaluatorFeedbackResponse(
                    status=feedback.status,
                    reason_code=feedback.reason_code,
                    evidence_snippet=feedback.evidence_snippet,
                )
            )

        return GetFeedbackResponse(feedback=tuple(tmp))

    except ForbiddenError as exc:
        return build_api_error_response(
            code="FORBIDDEN",
            message=exc.message,
            retryable=False,
            status_code=403,
            details=exc.details,
        )

    except Exception:
        logger.exception(
            "get evaluator feedback endpoint failed for session=%s", str(session_id)
        )
        return build_api_error_response(
            "INTERNAL_ERROR", "unexpected server error", False, 500, None
        )


@app.get(
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
            return build_api_error_response(
                code="SESSION_NOT_FOUND",
                message="Session not found",
                retryable=False,
                status_code=404,
                details={"session_id": str(session_id)},
            )

        events = repo.list_trace_events_for_session(session_id=session_id)
        learner_events = project_learner_visible_events(events=events)

        response: list[SessionTraceEvent] = []
        for event in learner_events:
            response.append(
                SessionTraceEvent(
                    id=event.event_id,
                    event_index=event.event_index,
                    family=event.family,
                    event_type=event.event_type,
                    source=event.source,
                    occurred_at=event.occurred_at,
                    payload=event.payload,
                )
            )

        return GetSessionTraceResponse(events=tuple(response))

    except ForbiddenErrorSessionQuery as exc:
        return build_api_error_response(
            code="FORBIDDEN",
            message=exc.message,
            retryable=False,
            status_code=403,
            details=exc.details,
        )
    except Exception:
        logger.exception(
            "get session trace endpoint failed for session=%s", str(session_id)
        )
        return build_api_error_response(
            code="INTERNAL_ERROR",
            message="unexpected server error",
            retryable=False,
            status_code=500,
            details=None,
        )


@app.post(
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
            return build_api_error_response(
                "SESSION_NOT_FOUND",
                "Session not found",
                False,
                404,
                {"session_id": str(session_id)},
            )

        if not session_metadata.interactive:
            return build_api_error_response(
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
            return build_api_error_response(
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

        email_input = InjectEmailInput(
            session_id=session_id,
            email_from=request.email_from,
            email_subject=request.email_subject,
            email_body=request.email_body,
            email_id=request.email_id,
            malicious=request.malicious,
            source=request.source,
        )

        await client.inject_email(input=email_input)

        attack_email_sent_payload: dict[str, object] = {
            "type": "attack_email_sent",
            "email_id": email_input.email_id,
            "email_from": email_input.email_from,
            "subject": email_input.email_subject,
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
                            str(bool(email_input.malicious)),
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
        return build_api_error_response(
            "FORBIDDEN", exc.message, False, 403, exc.details
        )

    except RuntimeClientError as exc:
        db.rollback()
        return build_api_error_response(
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            status_code=502,
            details={"session_id": str(session_id)},
        )
    except Exception:
        db.rollback()
        logger.exception("inject session email failed")
        return build_api_error_response(
            code="INTERNAL_ERROR",
            message="Unexpected server error",
            retryable=False,
            status_code=500,
            details={"session_id": str(session_id)},
        )


@app.post(
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
        return build_api_error_response(
            "INVALID_IDEMPOTENCY_KEY",
            "Valid Idempotency-Key header is required",
            False,
            400,
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
            return build_api_error_response(
                "SESSION_NOT_FOUND",
                "Session not found",
                False,
                404,
                {"session_id": str(session_id)},
            )

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
            return build_api_error_response(
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
            return build_api_error_response(
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
        return build_api_error_response(
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
        return build_api_error_response(
            code="FORBIDDEN",
            message=exc.message,
            retryable=False,
            status_code=403,
            details=exc.details,
        )
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
        return build_api_error_response(
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
        return build_api_error_response(
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
        return build_api_error_response(
            code="INTERNAL_SERVER_ERROR",
            message="Unknown error in explanation endpoint",
            retryable=False,
            status_code=500,
            details={"session_id": str(session_id)},
        )


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
