import asyncio
import logging
from datetime import datetime, timezone
from typing import cast
from uuid import UUID

from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from sqlalchemy.orm import Session
from apps.contracts.src.schemas import RuntimeStreamEvent
from apps.contracts.src.types import (
    TRACE_EVENT_ATTACK_EMAIL_SENT,
    TRACE_EVENT_MALICIOUS_EMAIL_READ,
    TRACE_EVENT_TOKEN_DISCLOSED,
    TRACE_EVENT_TOKEN_DISCLOSURE_ATTEMPTED,
    TRACE_EVENT_TOOL_CALL_FAILED,
    TRACE_EVENT_TOOL_CALL_REQUESTED,
    TRACE_EVENT_TOOL_CALL_SUCCEEDED,
    TraceFamily,
)

from apps.control_plane.src.application.runtime.errors import RuntimeClientError
from apps.control_plane.src.application.runtime.ports import RuntimeClientPort
from apps.control_plane.src.application.runtime.types import RunTurnInput
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.session_query.types import SessionMetadataDTO
from apps.control_plane.src.application.trace.ports import (
    TraceEventPort,
    TraceOutboxPort,
)
from apps.control_plane.src.application.session_stream.ports import (
    SessionStreamManagerPort,
)
from apps.control_plane.src.application.session_stream.messages import (
    build_agent_text_chunk_message,
    build_system_error_message,
)
from apps.control_plane.src.application.session_stream.payloads import (
    RuntimeEventPayload,
)

from .trace_events import append_model_turn_failed, append_runtime_event
from apps.control_plane.src.application.common.observability import log_fields

logger = logging.getLogger(__name__)

RUNTIME_EVENT_CONFIG: dict[
    str, tuple[TraceFamily, str, tuple[str, ...], tuple[str, ...]]
] = {
    "attack_email_sent": (
        "runtime",
        TRACE_EVENT_ATTACK_EMAIL_SENT,
        ("email_id", "recipient", "subject"),
        (),
    ),
    "try_attack_console_hint": (
        "runtime",
        "TRY_ATTACK_CONSOLE_HINT",
        ("message",),
        (),
    ),
    "tool_call_requested": (
        "tool",
        TRACE_EVENT_TOOL_CALL_REQUESTED,
        ("tool_name",),
        (
            "target_resource",
            "command",
            "operation",
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
        ),
    ),
    "tool_call_succeeded": (
        "tool",
        TRACE_EVENT_TOOL_CALL_SUCCEEDED,
        ("tool_name",),
        (
            "target_resource",
            "command",
            "operation",
            "deleted",
            "exists_after",
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
        ),
    ),
    "tool_call_failed": (
        "tool",
        TRACE_EVENT_TOOL_CALL_FAILED,
        ("tool_name",),
        (
            "target_resource",
            "command",
            "operation",
            "error_code",
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
        ),
    ),
    "malicious_email_read": (
        "runtime",
        TRACE_EVENT_MALICIOUS_EMAIL_READ,
        ("email_id", "subject", "malicious_marker"),
        (),
    ),
    "token_disclosure_attempted": (
        "runtime",
        TRACE_EVENT_TOKEN_DISCLOSURE_ATTEMPTED,
        ("channel", "target"),
        (),
    ),
    "token_disclosed": (
        "runtime",
        TRACE_EVENT_TOKEN_DISCLOSED,
        ("channel", "token_kind"),
        (),
    ),
}


def _build_event_payload(event: RuntimeStreamEvent) -> RuntimeEventPayload:
    config = RUNTIME_EVENT_CONFIG.get(event.type)
    if config is None:
        return RuntimeEventPayload(type=event.type)
    _, _, required_fields, optional_fields = config
    payload: dict[str, object] = {"type": event.type}
    for name in required_fields:
        payload[name] = getattr(event, name)
    for name in optional_fields:
        value = getattr(event, name, None)
        if value is not None:
            payload[name] = value
    return cast(RuntimeEventPayload, payload)


async def stream_runtime_turn(
    *,
    websocket: WebSocket,
    session_id: UUID,
    principal: PrincipalContext,
    metadata: SessionMetadataDTO,
    runtime_client: RuntimeClientPort,
    turn: RunTurnInput,
    turn_start: datetime,
    trace_repo: TraceEventPort,
    outbox_repo: TraceOutboxPort,
    db: Session,
    session_manager: SessionStreamManagerPort,
) -> tuple[bool, int, list[str]]:
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
                        **log_fields(
                            session_id=session_id,
                            lab_id=metadata.lab_id,
                            principal_id=principal.user_id,
                            turn_id=turn.turn_id,
                            idempotency_key=turn.idempotency_key,
                        ),
                        "event": "turn_failed_mid_stream",
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
                append_model_turn_failed(
                    trace_repo=trace_repo,
                    outbox_repo=outbox_repo,
                    session_id=session_id,
                    principal=principal,
                    metadata=metadata,
                    turn_start=turn_start,
                    error_code="TURN_FAILED_MID_STREAM",
                    phase="mid_stream",
                    chunks_emitted=chunks_emitted,
                )
                db.commit()
                return (False, chunks_emitted, full_response_text_parts)
            except WebSocketDisconnect:
                logger.info(
                    "turn stream client disconnected",
                    extra={
                        **log_fields(
                            session_id=session_id,
                            lab_id=metadata.lab_id,
                            principal_id=principal.user_id,
                            turn_id=turn.turn_id,
                            idempotency_key=turn.idempotency_key,
                        ),
                        "event": "turn_stream_disconnected",
                        "chunks_emitted": chunks_emitted,
                        "lab_difficulty": metadata.lab_difficulty,
                    },
                )
                db.commit()
                return (False, chunks_emitted, full_response_text_parts)
            except Exception:
                logger.exception(
                    "turn stream send failed",
                    extra={
                        **log_fields(
                            session_id=session_id,
                            lab_id=metadata.lab_id,
                            principal_id=principal.user_id,
                            turn_id=turn.turn_id,
                            idempotency_key=turn.idempotency_key,
                        ),
                        "event": "turn_failed_mid_stream",
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
                append_model_turn_failed(
                    trace_repo=trace_repo,
                    outbox_repo=outbox_repo,
                    session_id=session_id,
                    principal=principal,
                    metadata=metadata,
                    turn_start=turn_start,
                    error_code="TURN_FAILED_MID_STREAM",
                    phase="mid_stream",
                    chunks_emitted=chunks_emitted,
                )
                db.commit()
                return (False, chunks_emitted, full_response_text_parts)

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
            phase = "mid_stream" if first_chunk_emitted else "before_first_chunk"
            log_message = (
                "turn failed mid stream"
                if first_chunk_emitted
                else "turn failed before first chunk"
            )
            logger.warning(
                log_message,
                extra={
                    **log_fields(
                        session_id=session_id,
                        lab_id=metadata.lab_id,
                        principal_id=principal.user_id,
                        turn_id=turn.turn_id,
                        idempotency_key=turn.idempotency_key,
                    ),
                    "event": reason_code.lower(),
                    "reason_code": reason_code,
                    "retryable": getattr(event, "retryable", True),
                    "first_chunk_emitted": first_chunk_emitted,
                    "time_to_failure_ms": int(
                        (datetime.now(timezone.utc) - turn_start).total_seconds() * 1000
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
            append_model_turn_failed(
                trace_repo=trace_repo,
                outbox_repo=outbox_repo,
                session_id=session_id,
                principal=principal,
                metadata=metadata,
                turn_start=turn_start,
                error_code=reason_code,
                phase=phase,
                chunks_emitted=chunks_emitted,
            )
            db.commit()
            return (False, chunks_emitted, full_response_text_parts)

        if event.type == "turn_completed":
            completed = True
            break

        config = RUNTIME_EVENT_CONFIG.get(event.type)
        if config is None:
            continue

        family, normalized_event_type, _, _ = config
        payload = _build_event_payload(event)
        append_runtime_event(
            trace_repo=trace_repo,
            outbox_repo=outbox_repo,
            session_id=session_id,
            principal=principal,
            metadata=metadata,
            family=family,
            event_type=normalized_event_type,
            payload=payload,
        )

    if not completed:
        raise RuntimeClientError(
            code="RUNTIME_STREAM_INCOMPLETE",
            message="Runtime stream ended without terminal event",
            retryable=True,
        )

    return (True, chunks_emitted, full_response_text_parts)
