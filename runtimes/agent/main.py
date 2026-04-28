from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import monotonic
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from apps.contracts.src.schemas import (
    EmailArtifact,
    RunTurnStreamRequest,
    TextChunkEvent,
    TurnCompletedEvent,
    TurnFailedEvent,
    TurnStartedEvent,
)
from apps.agent_harness.src.application.session_loop.types import InboxItem
from apps.agent_harness.src.infrastructure.model.config import load_gateway_config
from apps.agent_harness.src.infrastructure.model.gateway_client import (
    GatewayModelClient,
)
from apps.agent_harness.src.infrastructure.tools.in_memory_file_tool import (
    InMemoryFileTool,
)
from apps.agent_harness.src.infrastructure.tools.in_memory_inbox_tool import (
    InMemoryInboxTool,
)
from apps.agent_harness.src.infrastructure.tools.in_memory_invoice_tool import (
    InMemoryInvoiceTool,
)

from .agent import GatewayLLMClient, run_agent_turn
from .tools import ToolCtx


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(lifespan=lifespan)

_INBOX = InMemoryInboxTool()
_FILES = InMemoryFileTool()
_INVOICE = InMemoryInvoiceTool()

_GATEWAY = GatewayModelClient(load_gateway_config())
_LLM = GatewayLLMClient(_GATEWAY)


def _make_ctx(session_id: UUID) -> ToolCtx:
    return ToolCtx(
        session_id=session_id,
        inbox=_INBOX,
        files=_FILES,
        invoice_memory=_INVOICE,
    )


@app.post("/runtime/v1/turns/stream")
async def stream_turn(request: RunTurnStreamRequest) -> StreamingResponse:
    if not request.prompt.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "invalid_request",
                "message": "prompt is empty",
                "retryable": False,
            },
        )

    ctx = _make_ctx(request.session_id)

    async def event_stream() -> AsyncIterator[str]:
        start = monotonic()
        chunks = 0
        yield TurnStartedEvent(type="turn_started").model_dump_json() + "\n"

        try:
            async for text in run_agent_turn(
                prompt=request.prompt,
                llm=_LLM,
                ctx=ctx,
            ):
                chunk_size = 24
                for i in range(0, len(text), chunk_size):
                    part = text[i : i + chunk_size]
                    is_final = (i + chunk_size >= len(text)) and True
                    yield (
                        TextChunkEvent(
                            type="text_chunk",
                            content=part,
                            chunk_index=chunks,
                            final=is_final,
                        ).model_dump_json()
                        + "\n"
                    )
                    chunks += 1

            duration_ms = int((monotonic() - start) * 1000)
            yield (
                TurnCompletedEvent(
                    type="turn_completed",
                    duration_ms=duration_ms,
                    chunks_emitted=chunks,
                ).model_dump_json()
                + "\n"
            )
        except Exception:
            yield (
                TurnFailedEvent(
                    type="turn_failed",
                    error_code="internal_error",
                    message="runtime turn failed",
                    retryable=True,
                ).model_dump_json()
                + "\n"
            )

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.post(
    "/runtime/v1/sessions/{session_id}/inbox/email",
    status_code=202,
)
def inject_inbox_email(
    session_id: UUID,
    request: EmailArtifact,
) -> dict[str, object]:
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
    _INBOX.receive_email(email=inbox_item)
    return {"session_id": str(session_id), "accepted": True}


@app.get("/healthz", status_code=200)
def health_status() -> dict[str, str]:
    return {"status": "ok"}
