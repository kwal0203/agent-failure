from typing import Protocol, Iterable
from .types import (
    ModelRequest,
    HarnessChunk,
    HarnessTurnInput,
    ChatMessage,
    HarnessFailure,
    InboxItem,
    ToolDecision,
    DeleteFileResult,
    ReadFileResult,
)


class ModelClientPort(Protocol):
    def stream(self, payload: ModelRequest) -> Iterable[HarnessChunk]: ...

    def complete(self, payload: ModelRequest) -> str: ...

    def decide_tool_or_text(self, payload: ModelRequest) -> ToolDecision: ...


class LabContextBuilderPort(Protocol):
    def build_messages(self, turn: HarnessTurnInput) -> list[ChatMessage]: ...


class EventSinkPort(Protocol):
    def on_chunk(self, chunk: HarnessChunk) -> None: ...
    def on_failure(self, failure: HarnessFailure) -> None: ...


class InboxToolPort(Protocol):
    def list_inbox(self) -> list[InboxItem]: ...

    def read_email(self, email_id: str) -> InboxItem | None: ...

    def receive_email(self, email: InboxItem) -> None: ...


class FileToolPort(Protocol):
    def read_file(self, path: str) -> ReadFileResult: ...

    def delete_file(self, path: str) -> DeleteFileResult: ...
