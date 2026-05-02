"""Websocket turn orchestration service."""

import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import WebSocket
from sqlalchemy.orm import Session

from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.prompt_classification.ports import (
    AuthorityBulletinClassifierPort,
)
from apps.control_plane.src.application.runtime.errors import RuntimeClientError
from apps.control_plane.src.application.runtime.ports import RuntimeClientFactoryPort
from apps.control_plane.src.application.runtime.types import RunTurnInput
from apps.control_plane.src.application.session_stream.ports import (
    SessionStreamManagerPort,
)
from apps.control_plane.src.infrastructure.persistence.outbox import SQLAlchemyOutbox
from apps.control_plane.src.interfaces.http.message_builders import (
    build_policy_denial_message,
    build_system_error_message,
    build_trace_event_message,
)

from .policy import (
    classify_authority_bulletin,
    get_runtime_binding_or_none,
    get_session_metadata_or_none,
    runtime_not_ready_message,
)
from .runtime_stream import stream_runtime_turn
from .idempotency import build_turn_idempotency_key
from .trace_events import (
    append_learner_prompt_trace,
    append_model_turn_completed,
    append_model_turn_started,
)
from .constants import LAB2_IDS

logger = logging.getLogger(__name__)


async def handle_user_prompt(
    websocket: WebSocket,
    session_id: UUID,
    principal: PrincipalContext,
    prompt_content: str,
    db: Session,
    runtime_client_factory: RuntimeClientFactoryPort,
    bulletin_classifier: AuthorityBulletinClassifierPort,
    session_manager: SessionStreamManagerPort,
):
    outbox_repo = SQLAlchemyOutbox(db=db)

    if not session_manager.try_begin_turn(session_id=session_id):
        await session_manager.send_to(
            websocket,
            build_policy_denial_message(
                session_id, "TURN_IN_PROGRESS", "Turn in progress"
            ),
        )
        return

    try:
        metadata = get_session_metadata_or_none(
            db=db, session_id=session_id, principal=principal
        )
        if metadata is None:
            await session_manager.send_to(
                websocket,
                build_policy_denial_message(
                    session_id, "SESSION_NOT_FOUND", "Session not found"
                ),
            )
            return

        if not metadata.interactive:
            await session_manager.send_to(
                websocket,
                build_policy_denial_message(
                    session_id, "SESSION_NOT_INTERACTIVE", "Session not interactive"
                ),
            )
            return

        if metadata.lab_id is None or metadata.lab_version_id is None:
            await session_manager.send_to(
                websocket,
                build_policy_denial_message(
                    session_id,
                    "SESSION_MISSING_CONTEXT",
                    "Session is missing lab context (lab id or lab version id)",
                ),
            )
            return

        runtime_binding = get_runtime_binding_or_none(db=db, session_id=session_id)
        if runtime_binding is None or runtime_binding.status != "ready":
            await session_manager.send_to(
                websocket,
                runtime_not_ready_message(
                    session_id=session_id,
                    runtime_binding=runtime_binding,
                    lab_difficulty=metadata.lab_difficulty,
                ),
            )
            return

        runtime_client = runtime_client_factory.create(
            base_url=runtime_binding.base_url
        )

        authority_decision = await classify_authority_bulletin(
            lab_id=metadata.lab_id,
            prompt_content=prompt_content,
            bulletin_classifier=bulletin_classifier,
        )

        trace_repo = append_learner_prompt_trace(
            db=db,
            outbox_repo=outbox_repo,
            session_id=session_id,
            prompt_content=prompt_content,
            principal=principal,
            metadata=metadata,
            authority_bulletin_passed=authority_decision.passed,
            authority_bulletin_runbook_action_type=authority_decision.runbook_action_type,
            authority_bulletin_destructive_db_delete=authority_decision.destructive_db_delete,
            include_authority_fields=metadata.lab_id in LAB2_IDS,
        )

        try:
            await session_manager.send_to(
                websocket,
                build_trace_event_message(session_id, "TURN_STARTED", "Turn started"),
            )
            await session_manager.send_to(
                websocket,
                build_trace_event_message(
                    session_id, "MODEL_REQUEST_STARTED", "Model request started"
                ),
            )

            append_model_turn_started(
                trace_repo=trace_repo,
                outbox_repo=outbox_repo,
                session_id=session_id,
                prompt_content=prompt_content,
                principal=principal,
                metadata=metadata,
            )

            turn_id = uuid4()
            turn = RunTurnInput(
                session_id=metadata.id,
                lab_id=metadata.lab_id,
                lab_version_id=metadata.lab_version_id,
                turn_id=turn_id,
                prompt=prompt_content,
                idempotency_key=build_turn_idempotency_key(
                    session_id=metadata.id, turn_id=turn_id
                ),
                authority_bulletin_passed=authority_decision.passed,
            )
            turn_start = datetime.now(timezone.utc)

            (
                completed,
                chunks_emitted,
                full_response_text_parts,
            ) = await stream_runtime_turn(
                websocket=websocket,
                session_id=session_id,
                principal=principal,
                metadata=metadata,
                runtime_client=runtime_client,
                turn=turn,
                turn_start=turn_start,
                trace_repo=trace_repo,
                outbox_repo=outbox_repo,
                db=db,
                session_manager=session_manager,
            )

            if not completed:
                return

            append_model_turn_completed(
                trace_repo=trace_repo,
                outbox_repo=outbox_repo,
                session_id=session_id,
                principal=principal,
                metadata=metadata,
                turn_start=turn_start,
                chunks_emitted=chunks_emitted,
                first_chunk_emitted=chunks_emitted > 0,
                full_response_text_parts=full_response_text_parts,
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
            await session_manager.send_to(
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
            await session_manager.send_to(
                websocket,
                build_system_error_message(
                    session_id, "INTERNAL_ERROR", "Unexpected server error"
                ),
            )
            return
    finally:
        session_manager.end_turn(session_id=session_id)
