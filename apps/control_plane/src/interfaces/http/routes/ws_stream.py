import logging
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from apps.control_plane.src.application.prompt_classification.ports import (
    AuthorityBulletinClassifierPort,
)
from apps.control_plane.src.application.runtime.ports import RuntimeClientFactoryPort
from apps.control_plane.src.application.session_query.errors import (
    ForbiddenErrorSessionQuery,
)
from apps.control_plane.src.application.session_query.service import (
    get_session_metadata,
)
from apps.control_plane.src.application.session_query.ports import (
    SessionMetadataRepository,
)
from apps.control_plane.src.application.session_stream.ports import (
    SessionStreamManagerPort,
)
from apps.control_plane.src.application.session_stream.service import handle_user_prompt
from apps.control_plane.src.application.common.observability import (
    log_fields,
    reset_correlation_id,
    set_correlation_id,
)
from apps.control_plane.src.interfaces.http.auth import (
    UnauthenticatedError,
    get_current_principal_ws,
)
from apps.control_plane.src.interfaces.http.dependencies import (
    get_authority_bulletin_classifier,
    get_request_db_session,
    get_runtime_client_factory,
    get_session_metadata_repository,
    get_ws_session_manager,
)
from apps.control_plane.src.interfaces.http.message_builders import (
    build_policy_denial_message,
    build_session_status_message,
)
from apps.control_plane.src.interfaces.http.stream_messages import UserPromptMessage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/api/v1/sessions/{session_id}/stream")
async def session_stream_ws(
    websocket: WebSocket,
    session_id: UUID,
    repo: SessionMetadataRepository = Depends(get_session_metadata_repository),
    db: Session = Depends(get_request_db_session),
    runtime_client_factory: RuntimeClientFactoryPort = Depends(
        get_runtime_client_factory
    ),
    bulletin_classifier: AuthorityBulletinClassifierPort = Depends(
        get_authority_bulletin_classifier
    ),
    session_manager: SessionStreamManagerPort = Depends(get_ws_session_manager),
) -> None:
    correlation_token = set_correlation_id(
        websocket.headers.get("x-correlation-id")
        or websocket.headers.get("x-request-id")
    )
    try:
        principal = get_current_principal_ws(websocket=websocket)
    except UnauthenticatedError:
        await websocket.close(code=1008, reason="unauthenticated")
        logger.warning(
            "session stream denied unauthenticated",
            extra=log_fields(session_id=session_id),
        )
        reset_correlation_id(correlation_token)
        return

    try:
        metadata = get_session_metadata(
            session_id=session_id,
            principal=principal,
            repo=repo,
        )
    except ForbiddenErrorSessionQuery:
        await websocket.close(code=1008, reason="forbidden")
        logger.warning(
            "session stream denied forbidden",
            extra={
                **log_fields(
                    session_id=session_id,
                    principal_id=principal.user_id,
                ),
                "role": principal.role,
            },
        )
        reset_correlation_id(correlation_token)
        return

    if metadata is None:
        await websocket.close(code=1008, reason="session not found")
        reset_correlation_id(correlation_token)
        return

    await session_manager.connect(session_id=session_id, websocket=websocket)
    logger.info(
        "session stream connect",
        extra={
            **log_fields(
                session_id=session_id,
                principal_id=principal.user_id,
                lab_id=metadata.lab_id,
            ),
            "role": principal.role,
        },
    )
    try:
        await session_manager.send_to(
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
                await session_manager.send_to(
                    websocket,
                    build_policy_denial_message(
                        session_id, "INVALID_MESSAGE", "Invalid websocket message shape"
                    ),
                )
                continue

            if prompt_msg.type != "USER_PROMPT":
                continue

            if prompt_msg.session_id != session_id:
                await session_manager.send_to(
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
                bulletin_classifier=bulletin_classifier,
                session_manager=session_manager,
            )

    except WebSocketDisconnect:
        pass
    finally:
        session_manager.disconnect(session_id=session_id, websocket=websocket)
        logger.info(
            "session stream disconnect",
            extra={
                **log_fields(
                    session_id=session_id,
                    principal_id=principal.user_id,
                    lab_id=metadata.lab_id,
                ),
                "role": principal.role,
            },
        )
        reset_correlation_id(correlation_token)
