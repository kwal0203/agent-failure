from .types import (
    ModelRequest,
    HarnessTurnInput,
    HarnessChunk,
    HarnessTurnResult,
    HarnessFailure,
)
from .ports import LabContextBuilderPort, ModelClientPort, EventSinkPort
from .errors import (
    SessionLoopInternalError,
    SessionLoopInvalidRequestError,
    SessionLoopProviderFailureError,
)


def run_single_turn(
    turn: HarnessTurnInput,
    model_client: ModelClientPort,
    event_sink: EventSinkPort,
    context_builder: LabContextBuilderPort,
) -> HarnessTurnResult:
    chunks: list[HarnessChunk] = []
    try:
        # TODO(E3-T2): Source `turn.prompt` from the USER_PROMPT ingress path once
        # websocket prompt admission/validation is wired into the harness call chain.
        messages = context_builder.build_messages(turn=turn)
        request = ModelRequest(messages=messages)
        # TODO(E5-T2): Replace local fake model client wiring with real gateway/provider
        # adapter that raises typed provider exceptions.
        for chunk in model_client.stream(payload=request):
            chunks.append(chunk)
            # TODO(E3-T3,E5-T4): Route chunk events to typed stream + durable trace sink
            # (control-plane websocket projection and persistent trace pipeline).
            event_sink.on_chunk(chunk=chunk)
        return HarnessTurnResult(chunks=chunks, failure=None)
    except SessionLoopInternalError as exc:
        failure = HarnessFailure(
            code="internal_error", message=exc.message, details=exc.details
        )
        # TODO(E3-T3,E5-T4): Emit typed failure stream message and durable failure trace.
        event_sink.on_failure(failure=failure)
        return HarnessTurnResult(chunks=chunks, failure=failure)
    except SessionLoopInvalidRequestError as exc:
        failure = HarnessFailure(
            code="invalid_request", message=exc.message, details=exc.details
        )
        # TODO(E3-T3,E5-T4): Emit typed denial/failure stream message and durable trace.
        event_sink.on_failure(failure=failure)
        return HarnessTurnResult(chunks=chunks, failure=failure)
    except SessionLoopProviderFailureError as exc:
        failure = HarnessFailure(
            code="provider_failure", message=exc.message, details=exc.details
        )
        # TODO(E3-T3,E5-T4): Emit typed provider failure stream message and durable trace.
        event_sink.on_failure(failure=failure)
        return HarnessTurnResult(chunks=chunks, failure=failure)
    except Exception as exc:
        failure = HarnessFailure(
            code="internal_error",
            message="Internal error in session loop",
            details={"error": str(exc)},
        )
        # TODO(E3-T3,E5-T4): Emit typed internal failure stream message and durable trace.
        event_sink.on_failure(failure=failure)
        return HarnessTurnResult(chunks=chunks, failure=failure)
