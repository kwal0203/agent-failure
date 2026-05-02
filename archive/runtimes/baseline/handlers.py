from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, UTC
import json
from typing import TYPE_CHECKING, Literal, Protocol, cast
from uuid import UUID

if TYPE_CHECKING:
    from .labs import LabHooks

from pydantic import ValidationError
from pydantic import RootModel

from apps.agent_harness.src.application.session_loop.ports import (
    FileToolPort,
    InboxToolPort,
    InvoiceMemoryToolPort,
)
from apps.agent_harness.src.application.session_loop.types import (
    InboxItem,
    MemoryType,
    ToolDecision,
    WriteMemoryInput,
)
from apps.contracts.src.schemas import (
    AttackEmailSentEvent,
    MaliciousEmailReadEvent,
    ToolCallRequestedEvent,
    ToolCallSucceededEvent,
    ToolCallFailedEvent,
)
from apps.contracts.src.types import CANONICAL_TOOL_ARGS_REQUIRED

from .types import EventItem, RuntimeExecutorItem, RuntimeTurnInput, TextItem


class WriteMemoryMetadataModel(RootModel[dict[str, str]]):
    pass


@dataclass
class TurnContext:
    turn: RuntimeTurnInput
    inbox_tool: InboxToolPort = field(default=None)  # type: ignore[assignment]
    file_tool: FileToolPort = field(default=None)  # type: ignore[assignment]
    invoice_memory_tool: InvoiceMemoryToolPort | None = None
    attack_seeded_sessions: set[UUID] = field(default_factory=lambda: set())
    urgent_malicious_context_by_session: dict[UUID, str] = field(
        default_factory=lambda: dict()
    )
    lab2_destructive_runbook_by_session: dict[UUID, bool] = field(
        default_factory=lambda: dict()
    )
    lab2_autonomous_delete_applied_sessions: set[UUID] = field(
        default_factory=lambda: set()
    )
    hooks: LabHooks | None = None

    @property
    def session_id(self) -> UUID:
        return self.turn.session_id

    @property
    def lab_id(self) -> UUID:
        return self.turn.lab_id


class ToolHandler(Protocol):
    def handle(
        self,
        decision: ToolDecision,
        ctx: TurnContext,
    ) -> list[RuntimeExecutorItem]: ...


class ListToolsHandler:
    def handle(
        self,
        decision: ToolDecision,
        ctx: TurnContext,
    ) -> list[RuntimeExecutorItem]:
        catalog = self._render_tool_catalog()
        return [
            EventItem(
                event=ToolCallRequestedEvent(
                    type="tool_call_requested",
                    tool_name="list_tools",
                    target_resource="tools",
                    operation="list",
                )
            ),
            EventItem(
                event=ToolCallSucceededEvent(
                    type="tool_call_succeeded",
                    tool_name="list_tools",
                    target_resource="tools",
                    operation="list",
                )
            ),
            TextItem(content=catalog),
        ]

    @staticmethod
    def _render_tool_catalog() -> str:
        lines = ["Available tools:"]
        for tool_name, required_args in CANONICAL_TOOL_ARGS_REQUIRED.items():
            if not required_args:
                lines.append(f"- {tool_name}()")
                continue
            args_csv = ", ".join(required_args)
            lines.append(f"- {tool_name}({args_csv})")
        return "\n".join(lines)


class ListInboxHandler:
    def handle(
        self,
        decision: ToolDecision,
        ctx: TurnContext,
    ) -> list[RuntimeExecutorItem]:
        items: list[RuntimeExecutorItem] = [
            EventItem(
                event=ToolCallRequestedEvent(
                    type="tool_call_requested",
                    tool_name="list_inbox",
                    target_resource="inbox",
                    operation="list",
                )
            ),
        ]

        inbox_items = ctx.inbox_tool.list_inbox()
        if ctx.session_id not in ctx.attack_seeded_sessions:
            malicious = next((x for x in inbox_items if x.malicious), None)
            if malicious is not None:
                items.append(
                    EventItem(
                        event=AttackEmailSentEvent(
                            type="attack_email_sent",
                            email_id=malicious.email_id,
                            recipient="learner@lab.local",
                            subject=malicious.email_subject,
                        )
                    )
                )
            ctx.attack_seeded_sessions.add(ctx.session_id)

        items.append(
            EventItem(
                event=ToolCallSucceededEvent(
                    type="tool_call_succeeded",
                    tool_name="list_inbox",
                    target_resource="inbox",
                    operation="list",
                )
            )
        )

        items.append(TextItem(content=self._render_inbox(inbox_items)))
        return items

    @staticmethod
    def _render_inbox(inbox_items: list[InboxItem]) -> str:
        if not inbox_items:
            return "Inbox is empty"

        email_id_to_alias, _ = _build_email_alias_maps(items=inbox_items)
        lines = ["Inbox:"]
        for item in inbox_items:
            body = item.email_body
            if not body and item.email_preview:
                body = item.email_preview
            display_id = email_id_to_alias.get(item.email_id, item.email_id)
            lines.append(f"ID: {display_id}")
            lines.append(f"Subject: {item.email_subject}")
            lines.append(f"Body: {body}")
            lines.append("")
        if lines[-1] == "":
            lines.pop()
        return "\n".join(lines)


def _build_email_alias_maps(
    *, items: list[InboxItem]
) -> tuple[dict[str, str], dict[str, str]]:
    email_id_to_alias: dict[str, str] = {}
    alias_to_email_id: dict[str, str] = {}
    for index, item in enumerate(items, start=1):
        alias = f"e{index}"
        email_id_to_alias[item.email_id] = alias
        alias_to_email_id[alias] = item.email_id
    return email_id_to_alias, alias_to_email_id


def _render_email(item: InboxItem, *, display_email_id: str | None = None) -> str:
    body = item.email_body
    if not body and item.email_preview:
        body = item.email_preview
    email_id = display_email_id or item.email_id
    return f"ID: {email_id}\nSubject: {item.email_subject}\nBody: {body}"


class ReadEmailHandler:
    def handle(
        self,
        decision: ToolDecision,
        ctx: TurnContext,
    ) -> list[RuntimeExecutorItem]:
        email_id = decision.args.get("email_id")
        items: list[RuntimeExecutorItem] = [
            EventItem(
                event=ToolCallRequestedEvent(
                    type="tool_call_requested",
                    tool_name="read_email",
                    target_resource=str(email_id) if email_id else None,
                    operation="read",
                )
            ),
        ]

        if not email_id:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="read_email",
                        operation="read",
                        error_code="MISSING_EMAIL_ID",
                    )
                )
            )
            items.append(TextItem(content="Missing required: email_id"))
            return items

        requested_email_id = str(email_id).strip()
        inbox_items = ctx.inbox_tool.list_inbox()
        email_id_to_alias, alias_to_email_id = _build_email_alias_maps(
            items=inbox_items
        )
        requested_email_id_key = requested_email_id.lower()
        resolved_email_id = alias_to_email_id.get(
            requested_email_id_key, requested_email_id
        )

        email_item = ctx.inbox_tool.read_email(email_id=resolved_email_id)
        if (
            email_item is None
            and requested_email_id
            and requested_email_id_key not in alias_to_email_id
            and not requested_email_id.startswith("email-")
        ):
            email_item = ctx.inbox_tool.read_email(
                email_id=f"email-{requested_email_id}"
            )

        if email_item is None:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="read_email",
                        target_resource=requested_email_id,
                        operation="read",
                        error_code="EMAIL_NOT_FOUND",
                    )
                )
            )
            items.append(
                TextItem(content=f"I couldn't find email '{requested_email_id}'")
            )
            return items

        items.append(
            EventItem(
                event=ToolCallSucceededEvent(
                    type="tool_call_succeeded",
                    tool_name="read_email",
                    target_resource=email_item.email_id,
                    operation="read",
                )
            )
        )

        if email_item.malicious:
            items.append(
                EventItem(
                    event=MaliciousEmailReadEvent(
                        type="malicious_email_read",
                        email_id=email_item.email_id,
                        subject=email_item.email_subject,
                        malicious_marker=email_item.malicious,
                    )
                )
            )
            if email_item.urgency_marker:
                ctx.urgent_malicious_context_by_session[ctx.session_id] = (
                    email_item.email_id
                )

        display_email_id = email_id_to_alias.get(
            email_item.email_id, email_item.email_id
        )
        items.append(
            TextItem(
                content=_render_email(
                    item=email_item, display_email_id=display_email_id
                )
            )
        )

        if ctx.hooks is not None:
            ctx.hooks.on_email_read(ctx, email_item, items)

        return items


class ReadFileHandler:
    def handle(
        self,
        decision: ToolDecision,
        ctx: TurnContext,
    ) -> list[RuntimeExecutorItem]:
        path = decision.args.get("path")
        items: list[RuntimeExecutorItem] = [
            EventItem(
                event=ToolCallRequestedEvent(
                    type="tool_call_requested",
                    tool_name="read_file",
                    target_resource=str(path) if path else None,
                    operation="read",
                )
            ),
        ]

        if not path:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="read_file",
                        operation="read",
                        error_code="MISSING_PATH",
                    )
                )
            )
            items.append(TextItem(content="Missing required: path"))
            return items

        file_result = ctx.file_tool.read_file(session_id=ctx.session_id, path=path)
        if file_result.error_code or file_result.content is None:
            self._handle_read_error(
                items=items,
                ctx=ctx,
                path=path,
                error_code=file_result.error_code or "FILE_NOT_FOUND",
            )
            return items

        items.append(
            EventItem(
                event=ToolCallSucceededEvent(
                    type="tool_call_succeeded",
                    tool_name="read_file",
                    target_resource=path,
                    operation="read",
                )
            )
        )
        items.append(TextItem(content=f"File {path}\n{file_result.content}"))
        return items

    def _handle_read_error(
        self,
        *,
        items: list[RuntimeExecutorItem],
        ctx: TurnContext,
        path: str,
        error_code: str,
    ) -> None:
        if ctx.hooks is not None:
            hook_items = ctx.hooks.on_read_file_error(ctx, path, error_code, items)
            items.extend(hook_items)
            if hook_items:
                return

        items.append(
            EventItem(
                event=ToolCallFailedEvent(
                    type="tool_call_failed",
                    tool_name="read_file",
                    target_resource=path,
                    operation="read",
                    error_code=error_code,
                )
            )
        )
        items.append(TextItem(content=f"I couldn't read file '{path}' ({error_code})"))


class WriteFileHandler:
    def handle(
        self,
        decision: ToolDecision,
        ctx: TurnContext,
    ) -> list[RuntimeExecutorItem]:
        path = decision.args.get("path")
        content = decision.args.get("content")
        items: list[RuntimeExecutorItem] = [
            EventItem(
                event=ToolCallRequestedEvent(
                    type="tool_call_requested",
                    tool_name="write_file",
                    target_resource=str(path) if path else None,
                    operation="write",
                )
            ),
        ]

        if not path:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="write_file",
                        operation="write",
                        error_code="MISSING_PATH",
                    )
                )
            )
            items.append(TextItem(content="Missing required: path"))
            return items

        if content is None:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="write_file",
                        target_resource=path,
                        operation="write",
                        error_code="MISSING_CONTENT",
                    )
                )
            )
            items.append(TextItem(content="Missing required: content"))
            return items

        write_result = ctx.file_tool.write_file(
            session_id=ctx.session_id,
            path=path,
            content=content,
        )
        items.append(
            EventItem(
                event=ToolCallSucceededEvent(
                    type="tool_call_succeeded",
                    tool_name="write_file",
                    target_resource=path,
                    operation="write",
                )
            )
        )
        items.append(
            TextItem(
                content=f"Wrote file '{write_result.path}' ({write_result.bytes_written} bytes)"
            )
        )
        return items


class DeleteFileHandler:
    def handle(
        self,
        decision: ToolDecision,
        ctx: TurnContext,
    ) -> list[RuntimeExecutorItem]:
        path = decision.args.get("path")
        items: list[RuntimeExecutorItem] = [
            EventItem(
                event=ToolCallRequestedEvent(
                    type="tool_call_requested",
                    tool_name="delete_file",
                    target_resource=str(path) if path else None,
                    operation="delete",
                )
            ),
        ]

        if not path:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="delete_file",
                        operation="delete",
                        error_code="MISSING_PATH",
                    )
                )
            )
            items.append(TextItem(content="Missing required: path"))
            return items

        delete_result = ctx.file_tool.delete_file(session_id=ctx.session_id, path=path)
        items.append(
            EventItem(
                event=ToolCallSucceededEvent(
                    type="tool_call_succeeded",
                    tool_name="delete_file",
                    target_resource=path,
                    operation="delete",
                    deleted=delete_result.deleted,
                    exists_after=delete_result.exists_after,
                )
            )
        )

        result_text = (
            f"Deleted file '{path}'"
            if delete_result.deleted
            else f"No file deleted for '{path}'"
        )
        items.append(TextItem(content=result_text))
        return items


class ReadInvoiceHandler:
    def handle(
        self,
        decision: ToolDecision,
        ctx: TurnContext,
    ) -> list[RuntimeExecutorItem]:
        invoice_id = decision.args.get("invoice_id")
        items: list[RuntimeExecutorItem] = [
            EventItem(
                event=ToolCallRequestedEvent(
                    type="tool_call_requested",
                    tool_name="read_invoice",
                    target_resource=str(invoice_id) if invoice_id else None,
                    operation="read",
                )
            ),
        ]

        if not invoice_id:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="read_invoice",
                        operation="read",
                        error_code="MISSING_INVOICE_ID",
                    )
                )
            )
            items.append(TextItem(content="Missing required: invoice_id"))
            return items

        if ctx.invoice_memory_tool is None:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="read_invoice",
                        target_resource=invoice_id,
                        operation="read",
                        error_code="INVOICE_TOOL_UNAVAILABLE",
                    )
                )
            )
            items.append(TextItem(content="Invoice tool is unavailable"))
            return items

        invoices = ctx.invoice_memory_tool.list_invoices(session_id=ctx.session_id)
        invoice = next(
            (item for item in invoices if item.invoice_id == invoice_id), None
        )
        if invoice is None:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="read_invoice",
                        target_resource=invoice_id,
                        operation="read",
                        error_code="INVOICE_NOT_FOUND",
                    )
                )
            )
            items.append(TextItem(content=f"I couldn't find invoice '{invoice_id}'"))
            return items

        items.append(
            EventItem(
                event=ToolCallSucceededEvent(
                    type="tool_call_succeeded",
                    tool_name="read_invoice",
                    target_resource=invoice_id,
                    operation="read",
                )
            )
        )
        items.append(
            TextItem(
                content=(
                    f"Invoice {invoice.invoice_id}\n"
                    f"Vendor: {invoice.vendor_name}\n"
                    f"Amount: {invoice.amount:.2f} {invoice.currency}"
                )
            )
        )
        return items


class LookupVendorMasterHandler:
    def handle(
        self,
        decision: ToolDecision,
        ctx: TurnContext,
    ) -> list[RuntimeExecutorItem]:
        vendor_name_raw = decision.args.get("vendor_name")
        lookup_vendor_name = (
            vendor_name_raw.strip()
            if isinstance(vendor_name_raw, str) and vendor_name_raw.strip()
            else None
        )
        items: list[RuntimeExecutorItem] = [
            EventItem(
                event=ToolCallRequestedEvent(
                    type="tool_call_requested",
                    tool_name="lookup_vendor_master",
                    target_resource=str(lookup_vendor_name)
                    if lookup_vendor_name
                    else None,
                    operation="lookup",
                )
            ),
        ]

        if not lookup_vendor_name:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="lookup_vendor_master",
                        operation="lookup",
                        error_code="MISSING_VENDOR_NAME",
                    )
                )
            )
            items.append(TextItem(content="Missing required: vendor_name"))
            return items

        if ctx.invoice_memory_tool is None:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="lookup_vendor_master",
                        target_resource=lookup_vendor_name,
                        operation="lookup",
                        error_code="INVOICE_TOOL_UNAVAILABLE",
                    )
                )
            )
            items.append(TextItem(content="Invoice tool is unavailable"))
            return items

        vendor_master = ctx.invoice_memory_tool.get_vendor_master(
            session_id=ctx.session_id, vendor_name=lookup_vendor_name
        )
        if vendor_master is None or vendor_master.vendor_name != lookup_vendor_name:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="lookup_vendor_master",
                        target_resource=lookup_vendor_name,
                        operation="lookup",
                        error_code="VENDOR_NOT_FOUND",
                    )
                )
            )
            items.append(
                TextItem(content=f"I couldn't find vendor '{lookup_vendor_name}'")
            )
            return items

        items.append(
            EventItem(
                event=ToolCallSucceededEvent(
                    type="tool_call_succeeded",
                    tool_name="lookup_vendor_master",
                    target_resource=lookup_vendor_name,
                    operation="lookup",
                )
            )
        )
        items.append(
            TextItem(
                content=(
                    f"Vendor {vendor_master.vendor_name}\n"
                    f"Official account: {vendor_master.official_account}\n"
                    f"Routing number: {vendor_master.routing_number}\n"
                    f"Status: {vendor_master.status}\n"
                    f"Last verified: {vendor_master.last_verified}"
                )
            )
        )
        return items


class RetrieveMemoryHandler:
    def handle(
        self,
        decision: ToolDecision,
        ctx: TurnContext,
    ) -> list[RuntimeExecutorItem]:
        query = decision.args.get("query")
        items: list[RuntimeExecutorItem] = [
            EventItem(
                event=ToolCallRequestedEvent(
                    type="tool_call_requested",
                    tool_name="retrieve_memory",
                    target_resource=str(query) if query else None,
                    operation="retrieve",
                )
            ),
        ]

        if not query:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="retrieve_memory",
                        operation="retrieve",
                        error_code="MISSING_QUERY",
                    )
                )
            )
            items.append(TextItem(content="Missing required: query"))
            return items

        if ctx.invoice_memory_tool is None:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="retrieve_memory",
                        target_resource=query,
                        operation="retrieve",
                        error_code="INVOICE_TOOL_UNAVAILABLE",
                    )
                )
            )
            items.append(TextItem(content="Invoice tool is unavailable"))
            return items

        memory_type: MemoryType | None = None
        if query in {
            "user_workflow_preferences",
            "vendor_profile_memory",
            "exception_handling_memory",
        }:
            memory_type = cast(MemoryType, query)

        memories = ctx.invoice_memory_tool.list_memory(
            session_id=ctx.session_id, memory_type=memory_type
        )
        items.append(
            EventItem(
                event=ToolCallSucceededEvent(
                    type="tool_call_succeeded",
                    tool_name="retrieve_memory",
                    target_resource=query,
                    operation="retrieve",
                )
            )
        )

        if not memories:
            items.append(TextItem(content=f"No memory found for query '{query}'"))
        else:
            lines = [f"Retrieved {len(memories)} memory record(s):"]
            for memory_item in memories:
                lines.append(
                    f"- [{memory_item.memory_type}] {memory_item.content} | trust={memory_item.provenance_trust} | source={memory_item.source_artifact_id}"
                )
            items.append(TextItem(content="\n".join(lines)))

        return items


class WriteMemoryHandler:
    def handle(
        self,
        decision: ToolDecision,
        ctx: TurnContext,
    ) -> list[RuntimeExecutorItem]:
        memory_type_raw = decision.args.get("memory_type")
        content = decision.args.get("content")
        metadata_raw = decision.args.get("metadata")
        items: list[RuntimeExecutorItem] = [
            EventItem(
                event=ToolCallRequestedEvent(
                    type="tool_call_requested",
                    tool_name="write_memory",
                    target_resource=str(memory_type_raw) if memory_type_raw else None,
                    operation="write",
                    memory_type=memory_type_raw,
                )
            ),
        ]

        if not memory_type_raw:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="write_memory",
                        operation="write",
                        error_code="MISSING_MEMORY_TYPE",
                    )
                )
            )
            items.append(TextItem(content="Missing required: memory_type"))
            return items

        if not content:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="write_memory",
                        target_resource=memory_type_raw,
                        operation="write",
                        error_code="MISSING_CONTENT",
                    )
                )
            )
            items.append(TextItem(content="Missing required: content"))
            return items

        if not metadata_raw:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="write_memory",
                        target_resource=memory_type_raw,
                        operation="write",
                        error_code="MISSING_METADATA",
                    )
                )
            )
            items.append(TextItem(content="Missing required: metadata"))
            return items

        if ctx.invoice_memory_tool is None:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="write_memory",
                        target_resource=memory_type_raw,
                        operation="write",
                        error_code="INVOICE_TOOL_UNAVAILABLE",
                    )
                )
            )
            items.append(TextItem(content="Invoice tool is unavailable"))
            return items

        if memory_type_raw not in {
            "user_workflow_preferences",
            "exception_handling_memory",
            "vendor_profile_memory",
        }:
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="write_memory",
                        target_resource=memory_type_raw,
                        operation="write",
                        error_code="INVALID_MEMORY_TYPE",
                    )
                )
            )
            items.append(
                TextItem(content=f"Unsupported memory_type '{memory_type_raw}'")
            )
            return items

        if memory_type_raw == "vendor_profile_memory":
            items.append(
                EventItem(
                    event=ToolCallFailedEvent(
                        type="tool_call_failed",
                        tool_name="write_memory",
                        target_resource=memory_type_raw,
                        operation="write",
                        error_code="VENDOR_PROFILE_MEMORY_WRITE_BLOCKED",
                    )
                )
            )
            items.append(
                TextItem(
                    content="Writing to the vendor master list is blocked by default. Only the CEO may change this list."
                )
            )
            return items

        metadata: dict[str, str]
        try:
            parsed = json.loads(metadata_raw)
            if isinstance(parsed, dict):
                metadata = WriteMemoryMetadataModel.model_validate(parsed).root
            else:
                metadata = {"raw": metadata_raw}
        except (json.JSONDecodeError, ValidationError):
            metadata = {"raw": metadata_raw}

        provenance_trust = metadata.get("provenance_trust", "untrusted")
        if provenance_trust not in {"trusted", "untrusted"}:
            provenance_trust = "untrusted"

        source_artifact_id = metadata.get("source_artifact_id", "artifact-unknown")
        source_artifact_type = metadata.get("source_artifact_type", "note")
        stored_at = metadata.get("stored_at") or (
            datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        )

        record = ctx.invoice_memory_tool.write_memory(
            session_id=ctx.session_id,
            item=WriteMemoryInput(
                memory_type=cast(MemoryType, memory_type_raw),
                content=content,
                metadata=metadata,
                source_artifact_id=source_artifact_id,
                source_artifact_type=source_artifact_type,
                provenance_trust=cast(
                    Literal["trusted", "untrusted"], provenance_trust
                ),
                stored_at=stored_at,
            ),
        )

        items.append(
            EventItem(
                event=ToolCallSucceededEvent(
                    type="tool_call_succeeded",
                    tool_name="write_memory",
                    target_resource=record.memory_type,
                    operation="write",
                    memory_type=record.memory_type,
                    provenance_trust=record.provenance_trust,
                    source_artifact_id=record.source_artifact_id,
                    source_artifact_type=record.source_artifact_type,
                )
            )
        )
        items.append(
            TextItem(
                content=(
                    f"Stored memory in {record.memory_type}\n"
                    f"Trust: {record.provenance_trust}\n"
                    f"Source artifact: {record.source_artifact_id}"
                )
            )
        )
        return items
