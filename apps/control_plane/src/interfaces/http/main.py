from fastapi import FastAPI, Depends, Request, Header, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime, timezone
from .schemas import (
    GetSessionMetadataResponse,
    SessionMetadataResponse,
    ApiErrorEnvelope,
    SessionResponse,
    CreateSessionResponse,
    CreateSessionRequest,
    GetLabsResponse,
    LabCatalogItemResponse,
    LabCapabilitiesResponse,
    EvaluatorFeedbackResponse,
    GetFeedbackResponse,
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
from apps.control_plane.src.application.common.errors import ForbiddenError
from apps.control_plane.src.application.session_create.service import create_session
from apps.control_plane.src.application.session_create.errors import (
    LabNotAvailableError,
    QuotaExceededError,
    RateLimitedError,
    DegradedModeRestrictionError,
    InvalidIdempotencyKeyError,
    AdmissionDecisionError,
)
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemyTraceEventRepository,
    SQLAlchemyEvaluatorRepository,
)
from apps.agent_harness.src.interfaces.runtime.local_loop import run_local_one_turn
from apps.agent_harness.src.application.session_loop.types import HarnessTurnInput
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
from .dependencies import (
    get_admission_policy,
    get_create_session_uow,
    get_session_metadata_repository,
)
from .auth import (
    Principal,
    UnauthenticatedError,
    get_current_principal,
    get_current_principal_ws,
)
from .stream_messages import (
    UserPromptMessage,
)
from .session_manager import WebSocketSessionManager
from .http_responses import build_api_error_response
from .message_builders import (
    build_policy_denial_message,
    build_agent_text_chunk_message,
    build_session_status_message,
    build_trace_event_message,
    build_system_error_message,
)
from .helpers import build_trace_event, build_model_turn_failed_payload

import logging
import asyncio
from uuid import uuid4
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
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db_session),
) -> GetSessionMetadataResponse | JSONResponse:
    repo = SQLAlchemySessionMetadataRepository(db=db)
    heartbeat_repo = SQLAlchemyWorkerHeartbeatRepository()

    try:
        session_metadata = get_session_metadata(
            session_id=session_id,
            principal_user_id=principal.user_id,
            principal_user_role=principal.role,
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

        http_obj = SessionMetadataResponse(
            id=session_metadata.id,
            lab_id=session_metadata.lab_id,
            lab_version_id=session_metadata.lab_version_id,
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
    principal: Principal = Depends(get_current_principal),
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
            idempotency_key=key,
            uow=uow,
        )
        session = SessionResponse(
            id=result.session_id,
            lab_id=result.lab_id,
            lab_version_id=result.lab_version_id,
            state=result.state,
            resume_mode=result.resume_mode,
            created_at=result.created_at,
        )

        return CreateSessionResponse(session=session)
    except LabNotAvailableError as exc:
        return build_api_error_response(
            "LAB_NOT_AVAILABLE", exc.message, False, 404, exc.details
        )
    except QuotaExceededError as exc:
        return build_api_error_response(
            "QUOTA_EXCEEDED", exc.message, False, 429, exc.details
        )
    except RateLimitedError as exc:
        return build_api_error_response(
            "RATE_LIMITED", exc.message, False, 429, exc.details
        )
    except DegradedModeRestrictionError as exc:
        return build_api_error_response(
            "DEGRADED_MODE_RESTRICTION", exc.message, False, 503, exc.details
        )
    except InvalidIdempotencyKeyError as exc:
        return build_api_error_response(
            "INVALID_IDEMPOTENCY_KEY", exc.message, False, 400, exc.details
        )
    except ForbiddenError as exc:
        return build_api_error_response(
            "FORBIDDEN", exc.message, False, 403, exc.details
        )
    except AdmissionDecisionError as exc:
        return build_api_error_response(
            "ADMISSION_DENIED", exc.message, False, 400, exc.details
        )
    except Exception:
        return build_api_error_response(
            "INTERNAL_ERROR", "unexpected server error", False, 500, None
        )


async def handle_user_prompt(
    websocket: WebSocket,
    session_id: UUID,
    principal: Principal,
    prompt_content: str,
    db: Session,
):
    repo = SQLAlchemySessionMetadataRepository(db=db)
    outbox_repo = SQLAlchemyOutbox(db=db)

    if not ws_manager.try_begin_turn(session_id=session_id):
        await ws_manager.send_to(
            websocket,
            build_policy_denial_message(
                session_id, "TURN_IN_PROGRESS", "Turn in progress"
            ),
        )
        return

    metadata = get_session_metadata(
        session_id=session_id,
        principal_user_id=principal.user_id,
        principal_user_role=principal.role,
        repo=repo,
    )
    try:
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
        )
        append_trace_event(trace=trace_event, repo=trace_repo, outbox_repo=outbox_repo)

        try:
            await ws_manager.send_to(
                websocket,
                build_trace_event_message(session_id, "TURN_STARTED", "Turn started"),
            )
            turn = HarnessTurnInput(
                session_id=metadata.id,
                lab_id=metadata.lab_id,
                lab_version_id=metadata.lab_version_id,
                prompt=prompt_content,
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
            )
            append_trace_event(
                trace=trace_event_model_started,
                repo=trace_repo,
                outbox_repo=outbox_repo,
            )

            turn_start = datetime.now(timezone.utc)
            first_chunk_emitted = False
            result = await asyncio.to_thread(run_local_one_turn, turn)
            if result.failure is not None and not first_chunk_emitted:
                reason_code = "TURN_FAILED_BEFORE_FIRST_CHUNK"
                user_message = (
                    "The assistant failed before responding. Please resend your prompt."
                )

                logger.warning(
                    "turn failed before first chunk",
                    extra={
                        "event": "turn_failed_before_first_chunk",
                        "session_id": str(session_id),
                        "reason_code": reason_code,
                        "retryable": True,
                        "first_chunk_emitted": False,
                        "time_to_failure_ms": int(
                            (datetime.now(timezone.utc) - turn_start).total_seconds()
                            * 1000
                        ),
                    },
                )

                await ws_manager.send_to(
                    websocket,
                    build_system_error_message(
                        session_id=session_id,
                        error_code=reason_code,
                        message=user_message,
                    ),
                )

                payload = build_model_turn_failed_payload(
                    error_code="TURN_FAILED_BEFORE_FIRST_CHUNK",
                    phase="before_first_chunk",
                    turn_start=turn_start,
                    chunks_emitted=0,
                )
                trace_event_model_failed = build_trace_event(
                    trace_repo=trace_repo,
                    session_id=session_id,
                    family="model",
                    event_type="MODEL_TURN_FAILED",
                    source="session_stream_service",
                    payload=payload,
                    actor_user_id=principal.user_id,
                    lab_id=metadata.lab_id,
                    lab_version_id=metadata.lab_version_id,
                )
                append_trace_event(
                    trace=trace_event_model_failed,
                    repo=trace_repo,
                    outbox_repo=outbox_repo,
                )

                db.commit()
                return

            full_response_text_parts: list[str] = []
            chunks_emitted = 0
            for chunk in result.chunks:
                try:
                    await asyncio.wait_for(
                        ws_manager.send_to(
                            websocket,
                            build_agent_text_chunk_message(
                                session_id, chunk.content, chunk.final
                            ),
                        ),
                        timeout=10.0,
                    )
                    first_chunk_emitted = True
                    chunks_emitted += 1
                    full_response_text_parts.append(chunk.content)
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

                    payload = build_model_turn_failed_payload(
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
                        payload=payload,
                        actor_user_id=principal.user_id,
                        lab_id=metadata.lab_id,
                        lab_version_id=metadata.lab_version_id,
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
                    )
                    append_trace_event(
                        trace=trace_event_model_failed,
                        repo=trace_repo,
                        outbox_repo=outbox_repo,
                    )

                    db.commit()
                    return

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
            )
            append_trace_event(
                trace=trace_event_model_completed,
                repo=trace_repo,
                outbox_repo=outbox_repo,
            )
            db.commit()
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
            principal_user_id=principal.user_id,
            principal_user_role=principal.role,
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
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db_session),
) -> GetLabsResponse | JSONResponse:
    lab_repo = SQLAlchemyLabRepository(db=db)
    application_principal = PrincipalContext(
        user_id=principal.user_id, role=principal.role
    )

    try:
        labs_for_principal = get_labs_for_principal(
            principal=application_principal, lab_repo=lab_repo
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
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db_session),
) -> GetFeedbackResponse | JSONResponse:
    repo = SQLAlchemyEvaluatorRepository(db=db)
    application_principal = PrincipalContext(
        user_id=principal.user_id, role=principal.role
    )

    try:
        evaluator_feedback = get_session_evaluator_feedback(
            principal=application_principal, session_id=session_id, repo=repo
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
