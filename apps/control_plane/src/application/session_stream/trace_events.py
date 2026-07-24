from datetime import datetime, timezone
from typing import Literal
from uuid import UUID, uuid4
from sqlalchemy.orm import Session

from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.session_query.types import SessionMetadataDTO
from apps.control_plane.src.application.trace.ports import (
    TraceEventPort,
    TraceOutboxPort,
)
from apps.control_plane.src.application.trace.service import append_trace_event
from apps.control_plane.src.application.trace.types import TraceEvent
from apps.control_plane.src.infrastructure.persistence.session_repository import (
    SQLAlchemyTraceEventRepository,
)
from apps.control_plane.src.application.session_stream.trace_builders import (
    build_model_turn_failed_payload,
    build_trace_event,
)
from apps.control_plane.src.application.session_stream.payloads import (
    LearnerPromptSubmittedPayload,
    ModelTurnCompletedPayload,
    ModelTurnStartedPayload,
    RuntimeEventPayload,
)
from apps.control_plane.src.application.common.observability import get_correlation_id


def append_learner_prompt_trace(
    *,
    db: Session,
    outbox_repo: TraceOutboxPort,
    session_id: UUID,
    prompt_content: str,
    principal: PrincipalContext,
    metadata: SessionMetadataDTO,
    authority_bulletin_passed: bool,
    authority_bulletin_runbook_action_type: str | None,
    authority_bulletin_destructive_db_delete: bool | None,
    include_authority_fields: bool,
) -> SQLAlchemyTraceEventRepository:
    trace_repo = SQLAlchemyTraceEventRepository(db=db)

    learner_payload: LearnerPromptSubmittedPayload = {
        "content": prompt_content,
        "role": "user",
        "channel": "websocket",
        "message_type": "USER_PROMPT",
    }
    if include_authority_fields:
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
        correlation_id=UUID(get_correlation_id()),
        request_id=None,
        actor_user_id=principal.user_id,
        lab_id=metadata.lab_id,
        lab_version_id=metadata.lab_version_id,
    )
    append_trace_event(trace=trace_event, repo=trace_repo, outbox_repo=outbox_repo)
    return trace_repo


def append_model_turn_started(
    *,
    trace_repo: TraceEventPort,
    outbox_repo: TraceOutboxPort,
    session_id: UUID,
    prompt_content: str,
    principal: PrincipalContext,
    metadata: SessionMetadataDTO,
) -> None:
    trace_event_model_started = build_trace_event(
        trace_repo=trace_repo,
        session_id=session_id,
        family="model",
        event_type="MODEL_TURN_STARTED",
        source="session_stream_service",
        payload=ModelTurnStartedPayload(
            provider="openrouter",
            message_type="USER_PROMPT",
            prompt_chars=len(prompt_content),
        ),
        actor_user_id=principal.user_id,
        lab_id=metadata.lab_id,
        lab_version_id=metadata.lab_version_id,
    )
    append_trace_event(
        trace=trace_event_model_started, repo=trace_repo, outbox_repo=outbox_repo
    )


def append_model_turn_failed(
    *,
    trace_repo: TraceEventPort,
    outbox_repo: TraceOutboxPort,
    session_id: UUID,
    principal: PrincipalContext,
    metadata: SessionMetadataDTO,
    turn_start: datetime,
    error_code: str,
    phase: str,
    chunks_emitted: int,
) -> None:
    payload = build_model_turn_failed_payload(
        error_code=error_code,
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
        payload=payload,
        actor_user_id=principal.user_id,
        lab_id=metadata.lab_id,
        lab_version_id=metadata.lab_version_id,
    )
    append_trace_event(
        trace=trace_event_model_failed, repo=trace_repo, outbox_repo=outbox_repo
    )


def append_model_turn_completed(
    *,
    trace_repo: TraceEventPort,
    outbox_repo: TraceOutboxPort,
    session_id: UUID,
    principal: PrincipalContext,
    metadata: SessionMetadataDTO,
    turn_start: datetime,
    chunks_emitted: int,
    first_chunk_emitted: bool,
    full_response_text_parts: list[str],
) -> None:
    trace_event_model_completed = build_trace_event(
        trace_repo=trace_repo,
        session_id=session_id,
        family="model",
        event_type="MODEL_TURN_COMPLETED",
        source="session_stream_service",
        payload=ModelTurnCompletedPayload(
            status="succeeded",
            chunks_emitted=chunks_emitted,
            duration_ms=int(
                (datetime.now(timezone.utc) - turn_start).total_seconds() * 1000
            ),
            first_chunk_emitted=first_chunk_emitted,
            content="".join(full_response_text_parts),
        ),
        actor_user_id=principal.user_id,
        lab_id=metadata.lab_id,
        lab_version_id=metadata.lab_version_id,
    )
    append_trace_event(
        trace=trace_event_model_completed, repo=trace_repo, outbox_repo=outbox_repo
    )


def append_runtime_event(
    *,
    trace_repo: TraceEventPort,
    outbox_repo: TraceOutboxPort,
    session_id: UUID,
    principal: PrincipalContext,
    metadata: SessionMetadataDTO,
    family: Literal["lifecycle", "learner", "runtime", "tool", "model"],
    event_type: str,
    payload: RuntimeEventPayload,
    occurred_at: datetime | None = None,
) -> None:
    signal_id = payload.get("signal_id")
    if isinstance(signal_id, str) and any(
        existing.event_type == event_type
        and existing.payload.get("signal_id") == signal_id
        for existing in trace_repo.list_trace_events_for_session(session_id=session_id)
    ):
        return

    trace_event = build_trace_event(
        trace_repo=trace_repo,
        session_id=session_id,
        family=family,
        event_type=event_type,
        source="session_stream_service",
        payload=payload,
        actor_user_id=principal.user_id,
        lab_id=metadata.lab_id,
        lab_version_id=metadata.lab_version_id,
        occurred_at=occurred_at,
    )
    append_trace_event(trace=trace_event, repo=trace_repo, outbox_repo=outbox_repo)
