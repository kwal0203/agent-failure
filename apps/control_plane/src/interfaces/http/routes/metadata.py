from datetime import datetime, timezone
import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.contracts.src.schemas import ApiErrorEnvelope
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.runtime.ports import RuntimeClientFactoryPort
from apps.control_plane.src.application.runtime.types import ReadRuntimeFileInput
from apps.control_plane.src.application.session_query.errors import (
    ForbiddenErrorSessionQuery,
)
from apps.control_plane.src.application.session_query.service import (
    get_session_metadata,
)
from apps.control_plane.src.infrastructure.persistence.db import get_db_session
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionMetadataRepository,
    SQLAlchemySessionRuntimeBindingRepository,
)
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.dependencies import (
    get_runtime_client_factory,
)
from apps.control_plane.src.interfaces.http.helpers import build_api_error_response
from apps.control_plane.src.interfaces.http.schemas import (
    GetSessionMetadataResponse,
    SessionFeedbackResponse,
    SessionHintResponse,
    SessionMetadataResponse,
    SessionProgressChipResponse,
    SessionRuntimeFileResponse,
)

PROVISIONING_STALL_SESSION_AGE_SECONDS = 360
PROVISIONING_STALL_HEARTBEAT_AGE_SECONDS = 360
AGENT_LAB_2_TOOL_MISUSE_ID = UUID("55555555-5555-5555-5555-555555555555")

logger = logging.getLogger(__name__)
router = APIRouter()


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.get(
    "/api/v1/sessions/{session_id}",
    response_model=GetSessionMetadataResponse,
    responses={
        401: {"model": ApiErrorEnvelope},
        403: {"model": ApiErrorEnvelope},
        404: {"model": ApiErrorEnvelope},
    },
)
async def get_metadata(
    session_id: UUID,
    principal: PrincipalContext = Depends(get_current_principal),
    db: Session = Depends(get_db_session),
    runtime_client_factory: RuntimeClientFactoryPort = Depends(
        get_runtime_client_factory
    ),
) -> GetSessionMetadataResponse | JSONResponse:
    repo = SQLAlchemySessionMetadataRepository(db=db)
    from apps.control_plane.src.interfaces.http import main as main_module

    heartbeat_repo = main_module.SQLAlchemyWorkerHeartbeatRepository()

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
        feedback: list[SessionFeedbackResponse] = []
        for feedback_item in session_metadata.feedback:
            feedback.append(
                SessionFeedbackResponse(
                    id=feedback_item.id,
                    feedback_key=feedback_item.feedback_key,
                    reason_code=feedback_item.reason_code,
                    message=feedback_item.message,
                    severity=feedback_item.severity,
                    trigger_event_index=feedback_item.trigger_event_index,
                    created_at=feedback_item.created_at,
                    seen_at=feedback_item.seen_at,
                )
            )

        runtime_files: list[SessionRuntimeFileResponse] = []
        agent_lab2_id = UUID("55555555-5555-5555-5555-555555555555")
        if session_metadata.lab_id == agent_lab2_id:
            try:
                runtime_binding_repo = SQLAlchemySessionRuntimeBindingRepository(db=db)
                runtime_binding = runtime_binding_repo.get_by_session_id(
                    session_id=session_id
                )
                if runtime_binding is not None and runtime_binding.status == "ready":
                    client = runtime_client_factory.create(
                        base_url=runtime_binding.base_url
                    )
                    runbook = await client.read_runtime_file(
                        ReadRuntimeFileInput(
                            session_id=session_id,
                            path="/var/secure/ops_runbook.md",
                        )
                    )
                    if isinstance(runbook.content, str) and runbook.content.strip():
                        runtime_files.append(
                            SessionRuntimeFileResponse(
                                path=runbook.path,
                                content=runbook.content,
                                updated_at=datetime.now(timezone.utc),
                            )
                        )
            except Exception:
                logger.warning(
                    "runtime file read failed in get_metadata", exc_info=True
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
            completion_status=session_metadata.completion_status,
            completed_at=session_metadata.completed_at,
            completion_reason_code=session_metadata.completion_reason_code,
            provisioning_stalled=stalled,
            provisioning_stall_reason_code="SESSION_PROVISIONING_STALLED"
            if stalled
            else None,
            progress_chips=progress_chips,
            hints=hints,
            unread_hint_count=session_metadata.unread_hint_count,
            feedback_items=feedback,
            feedback=feedback,
            unread_feedback_count=session_metadata.unread_feedback_count,
            runtime_files=runtime_files,
        )
        return GetSessionMetadataResponse(session=http_obj)

    except ForbiddenErrorSessionQuery as exc:
        return build_api_error_response(
            "FORBIDDEN", exc.message, False, 403, exc.details
        )
