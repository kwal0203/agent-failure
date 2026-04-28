from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import monotonic
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, HTTPException
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

from .agent import SYSTEM_PROMPT, GatewayLLMClient, run_agent_turn
from .auth import require_internal_auth
from .hooks import AgentLabHooks, NullAgentLabHooks
from .lab_configs import load_lab_config
from .lab_configs.lab_002_tool_misuse import Lab2Hooks
from .tools import ToolCtx, TOOLS, filter_tools
from .types import EventItem

import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield


app = FastAPI(lifespan=lifespan)

_INBOX = InMemoryInboxTool()
_FILES = InMemoryFileTool()
_INVOICE = InMemoryInvoiceTool()

_GATEWAY = GatewayModelClient(load_gateway_config())
_LLM = GatewayLLMClient(_GATEWAY)

_seeded_sessions: set[UUID] = set()


def _make_ctx(session_id: UUID) -> ToolCtx:
    return ToolCtx(
        session_id=session_id,
        inbox=_INBOX,
        files=_FILES,
        invoice_memory=_INVOICE,
    )


def _seed_lab(
    lab_id: UUID, ctx: ToolCtx, request: RunTurnStreamRequest | None = None
) -> AgentLabHooks:
    lab = load_lab_config(lab_id)
    if lab is not None and lab.seed is not None:
        for f in lab.seed.files:
            _FILES.seed_session_files(
                session_id=ctx.session_id,
                files={f.path: f.content},
                overwrite=False,
            )
        if lab.seed.memory:
            from apps.agent_harness.src.application.session_loop.types import (
                WriteMemoryInput,
            )
            import datetime

            for m in lab.seed.memory:
                _INVOICE.write_memory(
                    session_id=ctx.session_id,
                    item=WriteMemoryInput(
                        memory_type=m.memory_type,
                        content=m.content,
                        metadata=m.metadata,
                        source_artifact_id=m.source_artifact_id,
                        source_artifact_type=m.source_artifact_type,
                        provenance_trust=m.provenance_trust,
                        stored_at=datetime.datetime.now(
                            datetime.timezone.utc
                        ).isoformat(),
                    ),
                )

    hooks: AgentLabHooks = NullAgentLabHooks()
    if (
        lab is not None
        and hasattr(lab, "hooks_factory")
        and lab.hooks_factory is not None
    ):
        hooks = lab.hooks_factory()

    if ctx.session_id not in _seeded_sessions:
        hooks.seed(ctx)
        _seeded_sessions.add(ctx.session_id)

    if (
        isinstance(hooks, Lab2Hooks)
        and request is not None
        and request.authority_bulletin_passed
        and isinstance(request.authority_bulletin_signer, str)
        and request.authority_bulletin_signer.strip()
    ):
        hooks.apply_authority_bulletin(
            ctx=ctx,
            signer=request.authority_bulletin_signer.strip(),
            destructive_db_delete=bool(
                request.authority_bulletin_destructive_db_delete
            ),
        )

    return hooks


@app.post("/runtime/v1/turns/stream")
async def stream_turn(
    request: RunTurnStreamRequest,
    _auth: None = Depends(require_internal_auth),
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

    ctx = _make_ctx(request.session_id)
    lab = load_lab_config(request.lab_id)
    system_prompt = lab.system_prompt if lab is not None else SYSTEM_PROMPT
    active_tools = filter_tools(lab.enabled_tools) if lab is not None else TOOLS
    hooks = _seed_lab(request.lab_id, ctx, request)

    async def event_stream() -> AsyncIterator[str]:
        start = monotonic()
        chunks = 0
        yield (
            TurnStartedEvent(type="turn_started", runtime="agent").model_dump_json()
            + "\n"
        )

        try:
            async for item in run_agent_turn(
                prompt=request.prompt,
                llm=_LLM,
                ctx=ctx,
                system_prompt=system_prompt,
                tools=active_tools,
                hooks=hooks,
            ):
                if isinstance(item, EventItem):
                    yield item.event.model_dump_json() + "\n"
                else:
                    text = item.content
                    chunk_size = 24
                    for i in range(0, len(text), chunk_size):
                        part = text[i : i + chunk_size]
                        is_final = i + chunk_size >= len(text)
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
            logger.exception("Agent turn failed")
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
    _auth: None = Depends(require_internal_auth),
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
    return {"status": "ok", "runtime": "agent"}
