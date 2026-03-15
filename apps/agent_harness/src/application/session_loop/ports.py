from typing import Protocol, Iterable
from .types import (
    ModelRequest,
    HarnessChunk,
    HarnessTurnInput,
    ChatMessage,
    HarnessFailure,
)


class ModelClientPort(Protocol):
    def stream(self, payload: ModelRequest) -> Iterable[HarnessChunk]: ...


class LabContextBuilder(Protocol):
    def build_messages(self, turn: HarnessTurnInput) -> list[ChatMessage]: ...


class EventSinkPort(Protocol):
    def on_chunk(self, chunk: HarnessChunk) -> None: ...
    def on_failure(self, failure: HarnessFailure) -> None: ...
