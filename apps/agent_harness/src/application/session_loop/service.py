from .types import (
    ModelRequest,
    HarnessTurnInput,
    HarnessChunk,
    HarnessTurnResult,
    HarnessFailure,
)
from .ports import LabContextBuilder, ModelClientPort, EventSinkPort


def run_single_turn(
    turn: HarnessTurnInput,
    model_client: ModelClientPort,
    event_sink: EventSinkPort,
    context_builder: LabContextBuilder,
) -> HarnessTurnResult:
    chunks: list[HarnessChunk] = []
    try:
        messages = context_builder.build_messages(turn=turn)
        request = ModelRequest(messages=messages)
        for chunk in model_client.stream(payload=request):
            chunks.append(chunk)
            event_sink.on_chunk(chunk=chunk)
        return HarnessTurnResult(chunks=chunks, failure=None)
    # TODO: Need typed errors
    except ValueError as exc:
        failure = HarnessFailure(code="invalid_request", message=str(exc), details=None)
        event_sink.on_failure(failure=failure)
        return HarnessTurnResult(chunks=chunks, failure=failure)
    except Exception as exc:
        failure = HarnessFailure(
            code="provider_failure",
            message="model stream failed",
            details={"error": str(exc)},
        )
        event_sink.on_failure(failure=failure)
        return HarnessTurnResult(chunks=chunks, failure=failure)
