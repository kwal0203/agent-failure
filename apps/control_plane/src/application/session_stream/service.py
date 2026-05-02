"""Websocket turn orchestration service.

This module owns turn-level orchestration and persistence for session stream prompts.
"""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.prompt_classification.ports import (
    AuthorityBulletinClassifierPort,
)
from apps.control_plane.src.application.prompt_classification.types import (
    AuthorityBulletinClassificationInput,
)
from apps.control_plane.src.application.runtime.errors import RuntimeClientError
from apps.control_plane.src.application.runtime.ports import RuntimeClientFactoryPort
from apps.control_plane.src.application.runtime.types import RunTurnInput
from apps.control_plane.src.application.session_stream.ports import (
    SessionStreamManagerPort,
)
from apps.control_plane.src.application.session_query.service import (
    get_session_metadata,
)
from apps.control_plane.src.application.trace.service import append_trace_event
from apps.control_plane.src.application.trace.types import TraceEvent
from apps.control_plane.src.infrastructure.persistence.outbox import SQLAlchemyOutbox
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemySessionMetadataRepository,
    SQLAlchemySessionRuntimeBindingRepository,
    SQLAlchemyTraceEventRepository,
)
from apps.control_plane.src.interfaces.http.helpers import (
    build_model_turn_failed_payload,
    build_trace_event,
)
from apps.control_plane.src.interfaces.http.message_builders import (
    build_agent_text_chunk_message,
    build_policy_denial_message,
    build_system_error_message,
    build_trace_event_message,
)

LAB_2_TOOL_MISUSE_ID = UUID("22222222-2222-2222-2222-222222222222")
AGENT_LAB_2_TOOL_MISUSE_ID = UUID("55555555-5555-5555-5555-555555555555")
LAB2_AUTHORITY_SIGNER = "Morgan Hale"

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
    repo = SQLAlchemySessionMetadataRepository(db=db)
    outbox_repo = SQLAlchemyOutbox(db=db)
    runtime_binding_repo = SQLAlchemySessionRuntimeBindingRepository(db=db)

    if not session_manager.try_begin_turn(session_id=session_id):
        await session_manager.send_to(
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
            await session_manager.send_to(
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

        authority_bulletin_passed = False
        authority_bulletin_runbook_action_type: str | None = None
        authority_bulletin_destructive_db_delete: bool | None = None
        if metadata.lab_id in {LAB_2_TOOL_MISUSE_ID, AGENT_LAB_2_TOOL_MISUSE_ID}:
            try:
                classify = await bulletin_classifier.classify_prompt(
                    input=AuthorityBulletinClassificationInput(
                        prompt_content=prompt_content,
                        expected_signer=LAB2_AUTHORITY_SIGNER,
                    )
                )
                authority_bulletin_runbook_action_type = classify.runbook_action_type
                authority_bulletin_destructive_db_delete = (
                    classify.destructive_db_delete
                )
                authority_bulletin_passed = (
                    classify.is_authority_bulletin
                    and isinstance(classify.signer_name, str)
                    and classify.signer_name.strip().lower()
                    == LAB2_AUTHORITY_SIGNER.lower()
                )

            except RuntimeError:
                authority_bulletin_passed = False

        # TODO(P1-E6 follow-up): This writes learner trace directly via DB adapter
        # in the websocket handler. Move to UoW-backed trace write path so turn
        # handling and trace persistence share a clear transactional boundary.
        # learner trace
        trace_repo = SQLAlchemyTraceEventRepository(db=db)
        learner_payload: dict[str, object] = {
            # TODO(P1-E6/P1-E7 follow-up): Prompt content is persisted in full
            # for MVP evaluator/replay visibility. Revisit policy to decide
            # whether this should be redacted/summarized/hashed by default.
            "content": prompt_content,
            "role": "user",
            "channel": "websocket",
            "message_type": "USER_PROMPT",
        }

        if metadata.lab_id in {LAB_2_TOOL_MISUSE_ID, AGENT_LAB_2_TOOL_MISUSE_ID}:
            learner_payload["authority_bulletin_passed"] = authority_bulletin_passed
            learner_payload["authority_bulletin_runbook_action_type"] = (
                authority_bulletin_runbook_action_type
            )
            learner_payload["authority_bulletin_destructive_db_delete"] = (
                authority_bulletin_destructive_db_delete
            )

        trace_event = TraceEvent(
            event_id=uuid4(),
            session_id=session_id,
            family="learner",
            event_type="USER_PROMPT_SUBMITTED",
            occurred_at=datetime.now(timezone.utc),
            source="session_stream_service",
            event_index=trace_repo.get_next_event_index(session_id=session_id),
            payload=learner_payload,
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
                authority_bulletin_passed=authority_bulletin_passed,
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
                            session_manager.send_to(
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
                        await session_manager.send_to(
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
                        await session_manager.send_to(
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
                    await session_manager.send_to(
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

                if event.type == "try_attack_console_hint":
                    try_attack_console_hint_payload: dict[str, object] = {
                        "type": event.type,
                        "message": event.message,
                    }

                    trace_event = build_trace_event(
                        trace_repo=trace_repo,
                        session_id=session_id,
                        family="runtime",
                        event_type="TRY_ATTACK_CONSOLE_HINT",
                        source="session_stream_service",
                        payload=try_attack_console_hint_payload,
                        actor_user_id=principal.user_id,
                        lab_id=metadata.lab_id,
                        lab_version_id=metadata.lab_version_id,
                        lab_difficulty=metadata.lab_difficulty,
                    )

                    append_trace_event(
                        trace=trace_event, repo=trace_repo, outbox_repo=outbox_repo
                    )

                    continue

                if event.type == "tool_call_requested":
                    tool_call_requested_payload: dict[str, object] = {
                        "type": event.type,
                        "tool_name": event.tool_name,
                    }
                    if event.target_resource is not None:
                        tool_call_requested_payload["target_resource"] = (
                            event.target_resource
                        )
                    if event.command is not None:
                        tool_call_requested_payload["command"] = event.command
                    if event.operation is not None:
                        tool_call_requested_payload["operation"] = event.operation
                    for field_name in (
                        "memory_type",
                        "provenance_trust",
                        "source_artifact_id",
                        "source_artifact_type",
                        "invoice_id",
                        "vendor_name",
                        "vendor_id",
                        "amount",
                        "account_number",
                        "retrieved_memory_references",
                        "qualifying_log",
                        "log_case",
                    ):
                        field_value = getattr(event, field_name)
                        if field_value is not None:
                            tool_call_requested_payload[field_name] = field_value

                    trace_event = build_trace_event(
                        trace_repo=trace_repo,
                        session_id=session_id,
                        family="tool",
                        event_type="TOOL_CALL_REQUESTED",
                        source="session_stream_service",
                        payload=tool_call_requested_payload,
                        actor_user_id=principal.user_id,
                        lab_id=metadata.lab_id,
                        lab_version_id=metadata.lab_version_id,
                        lab_difficulty=metadata.lab_difficulty,
                    )

                    append_trace_event(
                        trace=trace_event, repo=trace_repo, outbox_repo=outbox_repo
                    )

                    continue

                if event.type == "tool_call_succeeded":
                    tool_call_succeeded_payload: dict[str, object] = {
                        "type": event.type,
                        "tool_name": event.tool_name,
                    }
                    if event.target_resource is not None:
                        tool_call_succeeded_payload["target_resource"] = (
                            event.target_resource
                        )
                    if event.command is not None:
                        tool_call_succeeded_payload["command"] = event.command
                    if event.operation is not None:
                        tool_call_succeeded_payload["operation"] = event.operation
                    if event.deleted is not None:
                        tool_call_succeeded_payload["deleted"] = event.deleted
                    if event.exists_after is not None:
                        tool_call_succeeded_payload["exists_after"] = event.exists_after
                    for field_name in (
                        "authority_bulletin_passed",
                        "authority_bulletin_destructive_db_delete",
                        "authority_bulletin_runbook_action_type",
                        "memory_type",
                        "provenance_trust",
                        "source_artifact_id",
                        "source_artifact_type",
                        "invoice_id",
                        "vendor_name",
                        "vendor_id",
                        "amount",
                        "account_number",
                        "retrieved_memory_references",
                        "qualifying_log",
                        "log_case",
                    ):
                        field_value = getattr(event, field_name)
                        if field_value is not None:
                            tool_call_succeeded_payload[field_name] = field_value

                    trace_event = build_trace_event(
                        trace_repo=trace_repo,
                        session_id=session_id,
                        family="tool",
                        event_type="TOOL_CALL_SUCCEEDED",
                        source="session_stream_service",
                        payload=tool_call_succeeded_payload,
                        actor_user_id=principal.user_id,
                        lab_id=metadata.lab_id,
                        lab_version_id=metadata.lab_version_id,
                        lab_difficulty=metadata.lab_difficulty,
                    )

                    append_trace_event(
                        trace=trace_event, repo=trace_repo, outbox_repo=outbox_repo
                    )

                    continue

                if event.type == "tool_call_failed":
                    tool_call_failed_payload: dict[str, object] = {
                        "type": event.type,
                        "tool_name": event.tool_name,
                    }
                    if event.target_resource is not None:
                        tool_call_failed_payload["target_resource"] = (
                            event.target_resource
                        )
                    if event.command is not None:
                        tool_call_failed_payload["command"] = event.command
                    if event.operation is not None:
                        tool_call_failed_payload["operation"] = event.operation
                    if event.error_code is not None:
                        tool_call_failed_payload["error_code"] = event.error_code
                    for field_name in (
                        "memory_type",
                        "provenance_trust",
                        "source_artifact_id",
                        "source_artifact_type",
                        "invoice_id",
                        "vendor_name",
                        "vendor_id",
                        "amount",
                        "account_number",
                        "retrieved_memory_references",
                        "qualifying_log",
                        "log_case",
                    ):
                        field_value = getattr(event, field_name)
                        if field_value is not None:
                            tool_call_failed_payload[field_name] = field_value

                    trace_event = build_trace_event(
                        trace_repo=trace_repo,
                        session_id=session_id,
                        family="tool",
                        event_type="TOOL_CALL_FAILED",
                        source="session_stream_service",
                        payload=tool_call_failed_payload,
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
