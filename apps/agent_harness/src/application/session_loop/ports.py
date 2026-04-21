from typing import Protocol, Iterable
from uuid import UUID
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
    VendorMasterRecord,
    AttackerTargetRecord,
    InvoiceRecord,
    MemoryRecord,
    WriteMemoryInput,
    MemoryType,
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
    def seed_session_files(
        self, *, session_id: UUID, files: dict[str, str], overwrite: bool = False
    ) -> None: ...

    def read_file(self, *, session_id: UUID, path: str) -> ReadFileResult: ...

    def delete_file(self, *, session_id: UUID, path: str) -> DeleteFileResult: ...


class InvoiceMemoryToolPort(Protocol):
    def seed_session_state(
        self, *, session_id: UUID, overwrite: bool = False
    ) -> None: ...

    def get_vendor_master(self, *, session_id: UUID) -> VendorMasterRecord | None: ...

    def get_attacker_target(
        self, *, session_id: UUID
    ) -> AttackerTargetRecord | None: ...

    def list_invoices(self, *, session_id: UUID) -> tuple[InvoiceRecord, ...]: ...

    def list_memory(
        self, *, session_id: UUID, memory_type: MemoryType | None = None
    ) -> tuple[MemoryRecord, ...]: ...

    def write_memory(
        self, *, session_id: UUID, item: WriteMemoryInput
    ) -> MemoryRecord: ...
