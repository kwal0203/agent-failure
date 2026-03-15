from collections.abc import Iterable
from uuid import UUID, uuid4

from apps.agent_harness.src.application.session_loop.service import run_single_turn
from apps.agent_harness.src.application.session_loop.types import (
    ChatMessage,
    HarnessChunk,
    HarnessFailure,
    HarnessTurnInput,
    ModelRequest,
)

from apps.agent_harness.src.application.session_loop.errors import (
    SessionLoopProviderFailureError,
)


class SpyModelClient:
    def __init__(self, chunks: list[HarnessChunk]) -> None:
        self._chunks = chunks
        self.last_payload: ModelRequest | None = None

    def stream(self, payload: ModelRequest) -> Iterable[HarnessChunk]:
        self.last_payload = payload
        for chunk in self._chunks:
            yield chunk


class FailingModelClient:
    def stream(self, payload: ModelRequest) -> Iterable[HarnessChunk]:
        _ = payload
        raise SessionLoopProviderFailureError(
            message="model stream failed", details={"provider": "openrouter"}
        )


class SpyContextBuilder:
    def build_messages(self, turn: HarnessTurnInput) -> list[ChatMessage]:
        return [
            ChatMessage(
                role="system",
                content=f"lab={turn.lab_id} version={turn.lab_version_id}",
            ),
            ChatMessage(role="user", content=turn.prompt),
        ]


class RecordingEventSink:
    def __init__(self) -> None:
        self.chunks: list[HarnessChunk] = []
        self.failures: list[HarnessFailure] = []

    def on_chunk(self, chunk: HarnessChunk) -> None:
        self.chunks.append(chunk)

    def on_failure(self, failure: HarnessFailure) -> None:
        self.failures.append(failure)


def _turn_input(
    *,
    session_id: UUID | None = None,
    lab_id: UUID | None = None,
    lab_version_id: UUID | None = None,
    prompt: str = "help me debug prompt injection",
) -> HarnessTurnInput:
    return HarnessTurnInput(
        session_id=session_id or uuid4(),
        lab_id=lab_id or uuid4(),
        lab_version_id=lab_version_id or uuid4(),
        prompt=prompt,
    )


def test_run_single_turn_success_from_prompt_to_streamed_response() -> None:
    turn = _turn_input(prompt="hello harness")
    sink = RecordingEventSink()
    client = SpyModelClient(
        chunks=[
            HarnessChunk(content="I can help with that. ", final=False),
            HarnessChunk(content="You asked: hello harness", final=True),
        ]
    )
    context = SpyContextBuilder()

    result = run_single_turn(
        turn=turn,
        model_client=client,
        event_sink=sink,
        context_builder=context,
    )

    assert result.failure is None
    assert len(result.chunks) == 2
    assert result.chunks[0].content == "I can help with that. "
    assert result.chunks[1].content == "You asked: hello harness"
    assert result.chunks[1].final is True


def test_run_single_turn_builds_model_request_from_context_builder() -> None:
    lab_id = UUID("11111111-1111-1111-1111-111111111111")
    lab_version_id = UUID("22222222-2222-2222-2222-222222222222")
    turn = _turn_input(
        lab_id=lab_id,
        lab_version_id=lab_version_id,
        prompt="inspect context path",
    )

    sink = RecordingEventSink()
    client = SpyModelClient(chunks=[HarnessChunk(content="ok", final=True)])
    context = SpyContextBuilder()

    _ = run_single_turn(
        turn=turn,
        model_client=client,
        event_sink=sink,
        context_builder=context,
    )

    assert client.last_payload is not None
    assert client.last_payload.messages[0].role == "system"
    assert str(lab_id) in client.last_payload.messages[0].content
    assert str(lab_version_id) in client.last_payload.messages[0].content
    assert client.last_payload.messages[1].role == "user"
    assert client.last_payload.messages[1].content == "inspect context path"


def test_run_single_turn_returns_provider_failure_when_model_stream_fails() -> None:
    turn = _turn_input()
    sink = RecordingEventSink()
    context = SpyContextBuilder()

    result = run_single_turn(
        turn=turn,
        model_client=FailingModelClient(),
        event_sink=sink,
        context_builder=context,
    )

    assert result.failure is not None
    assert result.failure.code == "provider_failure"
    assert result.failure.message == "model stream failed"
    assert result.failure.details == {"provider": "openrouter"}
    assert sink.failures
    assert sink.failures[0].code == "provider_failure"


def test_run_single_turn_emits_chunks_to_sink_in_stream_order() -> None:
    turn = _turn_input(prompt="ordered chunks")
    sink = RecordingEventSink()
    client = SpyModelClient(
        chunks=[
            HarnessChunk(content="chunk-1", final=False),
            HarnessChunk(content="chunk-2", final=False),
            HarnessChunk(content="chunk-3", final=True),
        ]
    )
    context = SpyContextBuilder()

    result = run_single_turn(
        turn=turn,
        model_client=client,
        event_sink=sink,
        context_builder=context,
    )

    assert [c.content for c in sink.chunks] == ["chunk-1", "chunk-2", "chunk-3"]
    assert [c.content for c in result.chunks] == ["chunk-1", "chunk-2", "chunk-3"]
