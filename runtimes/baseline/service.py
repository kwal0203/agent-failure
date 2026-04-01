from collections.abc import AsyncIterator
from time import monotonic
from apps.contracts.src.schemas import (
    TurnStartedEvent,
    TextChunkEvent,
    TurnCompletedEvent,
    RuntimeStreamEventType,
    TurnFailedEvent,
)
from apps.agent_harness.src.application.session_loop.ports import (
    ModelClientPort,
    LabContextBuilderPort,
    EventSinkPort,
)
from apps.agent_harness.src.application.session_loop.types import (
    ModelRequest,
    HarnessTurnInput,
)

from .types import RuntimeTurnInput


class RuntimeTurnExecutor:
    def __init__(
        self,
        *,
        model_client: ModelClientPort,
        context_builder: LabContextBuilderPort,
        event_sink: EventSinkPort,
    ) -> None:
        self._model_client = model_client
        self._context_builder = context_builder
        self._event_sink = event_sink

    async def stream_chunks(self, turn: RuntimeTurnInput) -> AsyncIterator[str]:
        harness_turn = HarnessTurnInput(
            session_id=turn.session_id,
            lab_id=turn.lab_id,
            lab_version_id=turn.lab_version_id,
            prompt=turn.prompt,
        )
        messages = self._context_builder.build_messages(turn=harness_turn)
        request = ModelRequest(messages=messages)

        for chunk in self._model_client.stream(payload=request):
            self._event_sink.on_chunk(chunk=chunk)
            yield chunk.content


async def stream_turn_events(
    input: RuntimeTurnInput,
    executor: RuntimeTurnExecutor,
) -> AsyncIterator[RuntimeStreamEventType]:
    start = monotonic()
    chunks_emitted = 0

    yield TurnStartedEvent(type="turn_started")

    try:
        aiter = executor.stream_chunks(turn=input)
        try:
            current = await anext(aiter)
        except StopAsyncIteration:
            current = None

        while current is not None:
            try:
                nxt = await anext(aiter)
                is_final = False
            except StopAsyncIteration:
                nxt = None
                is_final = True

            yield TextChunkEvent(
                type="text_chunk",
                content=current,
                chunk_index=chunks_emitted,
                final=is_final,
            )
            chunks_emitted += 1
            current = nxt

        duration_ms = int((monotonic() - start) * 1000)
        yield TurnCompletedEvent(
            type="turn_completed",
            duration_ms=duration_ms,
            chunks_emitted=chunks_emitted,
        )

    except Exception:
        yield TurnFailedEvent(
            type="turn_failed",
            error_code="internal_error",
            message="runtime turn failed",
            retryable=True,
        )
