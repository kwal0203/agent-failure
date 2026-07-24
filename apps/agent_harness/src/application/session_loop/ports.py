from typing import Protocol, Iterable
from uuid import UUID
from .types import (
    ModelRequest,
    HarnessChunk,
    InboxItem,
    ToolDecision,
    DeleteFileResult,
    ReadFileResult,
    WriteFileResult,
    VendorMasterRecord,
    AttackerTargetRecord,
    InvoiceRecord,
    MemoryRecord,
    WriteMemoryInput,
    MemoryType,
    AgentRequest,
    AgentResponse,
)


class ModelClientPort(Protocol):
    def stream(self, payload: ModelRequest) -> Iterable[HarnessChunk]: ...

    def complete(self, payload: ModelRequest) -> str: ...

    def decide_tool_or_text(self, payload: ModelRequest) -> ToolDecision: ...

    def agent_chat(self, payload: AgentRequest) -> AgentResponse: ...


class InboxToolPort(Protocol):
    def list_inbox(self) -> list[InboxItem]: ...

    def read_email(self, email_id: str) -> InboxItem | None: ...

    def receive_email(self, email: InboxItem) -> None: ...


class FileToolPort(Protocol):
    def seed_session_files(
        self, *, session_id: UUID, files: dict[str, str], overwrite: bool = False
    ) -> None: ...

    def read_file(self, *, session_id: UUID, path: str) -> ReadFileResult: ...
    def list_files(self, *, session_id: UUID) -> tuple[str, ...]: ...

    def write_file(
        self, *, session_id: UUID, path: str, content: str
    ) -> WriteFileResult: ...

    def delete_file(self, *, session_id: UUID, path: str) -> DeleteFileResult: ...


class InvoiceMemoryToolPort(Protocol):
    def seed_session_state(
        self, *, session_id: UUID, overwrite: bool = False
    ) -> None: ...

    def get_vendor_master(
        self, *, session_id: UUID, vendor_name: str
    ) -> VendorMasterRecord | None: ...

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
