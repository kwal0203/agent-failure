from __future__ import annotations

from uuid import UUID

from apps.agent_harness.src.application.session_loop.ports import (
    FileToolPort,
    InboxToolPort,
    InvoiceMemoryToolPort,
)
from apps.agent_harness.src.application.session_loop.types import (
    AttackerTargetRecord,
    DeleteFileResult,
    InboxItem,
    InvoiceRecord,
    MemoryRecord,
    MemoryType,
    ReadFileResult,
    VendorMasterRecord,
    WriteFileResult,
    WriteMemoryInput,
)


class StubInbox(InboxToolPort):
    def __init__(self) -> None:
        self._emails: dict[str, InboxItem] = {}

    def list_inbox(self) -> list[InboxItem]:
        return list(self._emails.values())

    def read_email(self, email_id: str) -> InboxItem | None:
        return self._emails.get(email_id)

    def receive_email(self, email: InboxItem) -> None:
        self._emails[email.email_id] = email


class StubFiles(FileToolPort):
    def __init__(self) -> None:
        self._files: dict[str, str] = {}

    def seed_session_files(
        self, *, session_id: UUID, files: dict[str, str], overwrite: bool = False
    ) -> None:
        _ = session_id
        if overwrite:
            self._files.update(files)
        else:
            for path, content in files.items():
                if path not in self._files:
                    self._files[path] = content

    def read_file(self, *, session_id: UUID, path: str) -> ReadFileResult:
        _ = session_id
        content = self._files.get(path)
        if content is None:
            return ReadFileResult(content=None, error_code="not_found")
        return ReadFileResult(content=content)

    def write_file(
        self, *, session_id: UUID, path: str, content: str
    ) -> WriteFileResult:
        _ = session_id
        self._files[path] = content
        return WriteFileResult(path=path, bytes_written=len(content.encode()))

    def delete_file(self, *, session_id: UUID, path: str) -> DeleteFileResult:
        _ = session_id
        if path in self._files:
            del self._files[path]
            return DeleteFileResult(deleted=True, exists_after=False)
        return DeleteFileResult(deleted=False, exists_after=False)


class StubInvoiceMemory(InvoiceMemoryToolPort):
    def __init__(self) -> None:
        self._vendors: dict[str, VendorMasterRecord] = {}
        self._invoices: list[InvoiceRecord] = []
        self._memories: list[MemoryRecord] = []

    def seed_session_state(self, *, session_id: UUID, overwrite: bool = False) -> None:
        _ = session_id
        _ = overwrite

    def get_vendor_master(
        self, *, session_id: UUID, vendor_name: str
    ) -> VendorMasterRecord | None:
        _ = session_id
        return self._vendors.get(vendor_name)

    def get_attacker_target(self, *, session_id: UUID) -> AttackerTargetRecord | None:
        _ = session_id
        return None

    def list_invoices(self, *, session_id: UUID) -> tuple[InvoiceRecord, ...]:
        _ = session_id
        return tuple(self._invoices)

    def list_memory(
        self, *, session_id: UUID, memory_type: MemoryType | None = None
    ) -> tuple[MemoryRecord, ...]:
        _ = session_id
        _ = memory_type
        return tuple(self._memories)

    def write_memory(self, *, session_id: UUID, item: WriteMemoryInput) -> MemoryRecord:
        _ = session_id
        record = MemoryRecord(
            memory_type=item.memory_type,
            content=item.content,
            metadata=item.metadata,
            source_artifact_id=item.source_artifact_id,
            source_artifact_type=item.source_artifact_type,
            provenance_trust=item.provenance_trust,
            stored_at=item.stored_at,
        )
        self._memories.append(record)
        return record

    def add_vendor(self, vendor: VendorMasterRecord) -> None:
        self._vendors[vendor.vendor_name] = vendor

    def add_invoice(self, invoice: InvoiceRecord) -> None:
        self._invoices.append(invoice)
