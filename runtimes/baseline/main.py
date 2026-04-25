from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from apps.contracts.src.schemas import RunTurnStreamRequest, EmailArtifact
from uuid import UUID, uuid4
from apps.agent_harness.src.application.session_loop.types import InboxItem

from .auth import require_internal_auth
from .schemas import HealthStatus, InjectEmailResponse
from .types import RuntimeTurnInput
from .service import stream_turn_events, RuntimeTurnExecutor
from .dependencies import get_runtime_executor


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/runtime/v1/turns/stream")
async def stream_turn(
    request: RunTurnStreamRequest,
    _: None = Depends(require_internal_auth),
    executor: RuntimeTurnExecutor = Depends(get_runtime_executor),
) -> StreamingResponse:
    if not request.prompt.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "invalid_request",
                "message": "prompt is empty",
                "retryable": False,
            },
        )

    turn_input = RuntimeTurnInput(
        session_id=request.session_id,
        lab_id=request.lab_id,
        lab_version_id=request.lab_version_id,
        turn_id=request.turn_id,
        prompt=request.prompt,
        idempotency_key=request.idempotency_key,
        authority_bulletin_passed=request.authority_bulletin_passed,
        authority_bulletin_signer=request.authority_bulletin_signer,
    )

    async def event_stream():
        async for event in stream_turn_events(input=turn_input, executor=executor):
            yield event.model_dump_json() + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.post(
    "/runtime/v1/sessions/{session_id}/inbox/email",
    response_model=InjectEmailResponse,
    status_code=202,
)
def inject_inbox_email(
    session_id: UUID,
    request: EmailArtifact,
    executor: RuntimeTurnExecutor = Depends(get_runtime_executor),
    _: None = Depends(require_internal_auth),
) -> InjectEmailResponse:

    inbox_item = InboxItem(
        email_id=request.email_id or f"u-{uuid4().hex[:8]}",
        email_from=request.email_from,
        email_subject=request.email_subject,
        email_body=request.email_body,
        email_preview=request.email_preview,
        malicious=bool(request.malicious),
        urgency_marker=bool(request.urgency_marker),
        source=request.source,
    )

    executor.inject_email_into_inbox(inbox_item=inbox_item)
    # TODO(lab1): Endpoint currently returns accepted=True once in-memory append
    # succeeds. Add durable inbox artifact persistence/idempotency and explicit
    # rejection/failure codes when business checks reject injection.
    return InjectEmailResponse(session_id=session_id)


@app.get("/healthz", status_code=200)
def health_status() -> dict[str, str]:
    return HealthStatus(status="ok").model_dump(mode="json")
