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
from apps.control_plane.src.infrastructure.persistence.worker_heartbeat_repository import (
    SQLAlchemyWorkerHeartbeatRepository,
)
from apps.control_plane.src.interfaces.http.auth import get_current_principal
from apps.control_plane.src.interfaces.http.dependencies import (
    get_runtime_client_factory,
)
from apps.control_plane.src.interfaces.http.errors import (
    forbidden,
    session_not_found,
)
from apps.control_plane.src.interfaces.http.mappers.session_mapper import (
    build_runtime_file_response,
    map_session_metadata_response,
)
from apps.control_plane.src.interfaces.http.schemas import (
    GetSessionMetadataResponse,
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
    heartbeat_repo = SQLAlchemyWorkerHeartbeatRepository()

    try:
        session_metadata = get_session_metadata(
            session_id=session_id,
            principal=principal,
            repo=repo,
        )
        if session_metadata is None:
            return session_not_found(str(session_id))

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

        runtime_files: list[SessionRuntimeFileResponse] = []
        if session_metadata.lab_id == AGENT_LAB_2_TOOL_MISUSE_ID:
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
                            build_runtime_file_response(
                                path=runbook.path,
                                content=runbook.content,
                            )
                        )
            except Exception:
                logger.warning(
                    "runtime file read failed in get_metadata", exc_info=True
                )

        http_obj = map_session_metadata_response(
            session_metadata=session_metadata,
            provisioning_stalled=stalled,
            runtime_files=runtime_files,
        )
        return GetSessionMetadataResponse(session=http_obj)

    except ForbiddenErrorSessionQuery as exc:
        return forbidden(exc.message, exc.details)
