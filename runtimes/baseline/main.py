from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from apps.contracts.src.schemas import RunTurnStreamRequest

from .auth import require_internal_auth
from .schemas import HealthStatus
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
    )

    async def event_stream():
        async for event in stream_turn_events(input=turn_input, executor=executor):
            yield event.model_dump_json() + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@app.get("/healthz", status_code=200)
def health_status() -> dict[str, str]:
    return HealthStatus(status="ok").model_dump(mode="json")
