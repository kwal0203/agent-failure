from __future__ import annotations

import json
from uuid import UUID
from dataclasses import dataclass
from typing import Protocol, Any, cast

from apps.agent_harness.src.application.session_loop.ports import (
    InboxToolPort,
    FileToolPort,
    InvoiceMemoryToolPort,
)
from apps.agent_harness.src.application.session_loop.types import (
    WriteMemoryInput,
)

from .types import ToolDef, ToolCall, ToolResult


def _string_schema(description: str) -> dict[str, object]:
    return {"type": "string", "description": description}


def _make_properties(**fields: str) -> dict[str, object]:
    props: dict[str, object] = {}
    for name, desc in fields.items():
        props[name] = _string_schema(desc)
    return props


TOOLS: list[ToolDef] = [
    ToolDef(
        name="list_tools",
        description="List all available tools and their descriptions.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    ToolDef(
        name="list_files",
        description="List all available file paths in the current session.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    ToolDef(
        name="list_inbox",
        description="List all emails in the inbox.",
        parameters={
            "type": "object",
            "properties": {},
            "required": [],
        },
    ),
    ToolDef(
        name="read_email",
        description="Read the full content of a specific email.",
        parameters={
            "type": "object",
            "properties": _make_properties(
                email_id="The ID of the email to read",
            ),
            "required": ["email_id"],
        },
    ),
    ToolDef(
        name="read_file",
        description="Read the content of a file at the given path.",
        parameters={
            "type": "object",
            "properties": _make_properties(
                path="The file path to read",
            ),
            "required": ["path"],
        },
    ),
    ToolDef(
        name="write_file",
        description="Write content to a file at the given path.",
        parameters={
            "type": "object",
            "properties": _make_properties(
                path="The file path to write to",
                content="The content to write",
            ),
            "required": ["path", "content"],
        },
    ),
    ToolDef(
        name="delete_file",
        description="Delete a file at the given path.",
        parameters={
            "type": "object",
            "properties": _make_properties(
                path="The file path to delete",
            ),
            "required": ["path"],
        },
    ),
    ToolDef(
        name="read_invoice",
        description="Read the details of a specific invoice.",
        parameters={
            "type": "object",
            "properties": _make_properties(
                invoice_id="The ID of the invoice to read",
            ),
            "required": ["invoice_id"],
        },
    ),
    ToolDef(
        name="lookup_vendor_master",
        description="Look up vendor master record by vendor name.",
        parameters={
            "type": "object",
            "properties": _make_properties(
                vendor_name="The vendor name to look up",
            ),
            "required": ["vendor_name"],
        },
    ),
    ToolDef(
        name="retrieve_memory",
        description="Retrieve stored memory records by query.",
        parameters={
            "type": "object",
            "properties": _make_properties(
                query="The search query for memory retrieval",
            ),
            "required": ["query"],
        },
    ),
    ToolDef(
        name="write_memory",
        description="Write a new memory record.",
        parameters={
            "type": "object",
            "properties": _make_properties(
                memory_type="The type of memory",
                content="The memory content",
                metadata="JSON metadata for the memory",
            ),
            "required": ["memory_type", "content", "metadata"],
        },
    ),
    ToolDef(
        name="pay_invoice",
        description="Pay a vendor invoice by specifying vendor, account, amount, and invoice ID.",
        parameters={
            "type": "object",
            "properties": _make_properties(
                vendor_name="The vendor name",
                account_number="The account number to pay to",
                amount="The payment amount",
                invoice_id="The invoice ID to pay",
            ),
            "required": ["vendor_name", "account_number", "amount", "invoice_id"],
        },
    ),
]

TOOL_DEFS_BY_NAME: dict[str, ToolDef] = {t.name: t for t in TOOLS}


def filter_tools(enabled: tuple[str, ...]) -> list[ToolDef]:
    return [TOOL_DEFS_BY_NAME[name] for name in enabled if name in TOOL_DEFS_BY_NAME]


@dataclass(frozen=True)
class ToolCtx:
    session_id: UUID
    inbox: InboxToolPort
    files: FileToolPort
    lab_id: UUID | None = None
    invoice_memory: InvoiceMemoryToolPort | None = None
    available_tools: tuple[ToolDef, ...] = tuple(TOOLS)
    authority_bulletin_passed: bool | None = None


def _handle_list_tools(ctx: ToolCtx, args: dict[str, object]) -> str:
    lines: list[str] = ["<ul>"]
    for t in ctx.available_tools:
        lines.append(f"<li><strong>{t.name}</strong>: {t.description}</li>")
    lines.append("</ul>")
    return "\n".join(lines)


def _handle_list_files(ctx: ToolCtx, args: dict[str, object]) -> str:
    _ = args
    paths = ctx.files.list_files(session_id=ctx.session_id)
    if not paths:
        return "No files available."
    lines: list[str] = ["<ul>"]
    for path in paths:
        lines.append(f"<li>{path}</li>")
    lines.append("</ul>")
    return "\n".join(lines)


def _handle_list_inbox(ctx: ToolCtx, args: dict[str, object]) -> str:
    items = ctx.inbox.list_inbox()
    if not items:
        return "Inbox is empty."
    lines: list[str] = []
    for item in items:
        preview = item.email_preview or item.email_body[:80]
        lines.append(
            f"[{item.email_id}] From: {item.email_from} | Subject: {item.email_subject} | Preview: {preview}"
        )
    return "\n".join(lines)


def _handle_read_email(ctx: ToolCtx, args: dict[str, object]) -> str:
    email_id = str(args.get("email_id", ""))
    item = ctx.inbox.read_email(email_id)
    if item is None:
        return f"Email not found: {email_id}"
    return (
        f"From: {item.email_from}\nSubject: {item.email_subject}\n\n{item.email_body}"
    )


def _handle_read_file(ctx: ToolCtx, args: dict[str, object]) -> str:
    path = str(args.get("path", ""))
    result = ctx.files.read_file(session_id=ctx.session_id, path=path)
    if result.content is None:
        return f"ERROR(FILE_NOT_FOUND): {path}"
    return result.content


def _handle_write_file(ctx: ToolCtx, args: dict[str, object]) -> str:
    path = str(args.get("path", ""))
    content = str(args.get("content", ""))
    result = ctx.files.write_file(session_id=ctx.session_id, path=path, content=content)
    return f"Written {result.bytes_written} bytes to {result.path}"


def _handle_delete_file(ctx: ToolCtx, args: dict[str, object]) -> str:
    path = str(args.get("path", ""))
    result = ctx.files.delete_file(session_id=ctx.session_id, path=path)
    if result.deleted:
        return f"Deleted: {path}"
    return f"File not found or already deleted: {path}"


def _handle_read_invoice(ctx: ToolCtx, args: dict[str, object]) -> str:
    if ctx.invoice_memory is None:
        return "Invoice tool not available."
    invoice_id = str(args.get("invoice_id", ""))
    invoices = ctx.invoice_memory.list_invoices(session_id=ctx.session_id)
    for inv in invoices:
        if inv.invoice_id == invoice_id:
            return (
                f"Invoice ID: {inv.invoice_id}\n"
                f"Vendor: {inv.vendor_name} (ID: {inv.vendor_id})\n"
                f"Amount: {inv.amount} {inv.currency}"
            )
    return f"Invoice not found: {invoice_id}"


def _handle_lookup_vendor_master(ctx: ToolCtx, args: dict[str, object]) -> str:
    if ctx.invoice_memory is None:
        return "Vendor lookup not available."
    vendor_name = str(args.get("vendor_name", ""))
    record = ctx.invoice_memory.get_vendor_master(
        session_id=ctx.session_id, vendor_name=vendor_name
    )
    if record is None:
        return f"Vendor not found: {vendor_name}"
    return (
        f"Vendor: {record.vendor_name} (ID: {record.vendor_id})\n"
        f"Account: {record.official_account}\n"
        f"Routing: {record.routing_number}\n"
        f"Status: {record.status}\n"
        f"Last Verified: {record.last_verified}"
    )


def _handle_retrieve_memory(ctx: ToolCtx, args: dict[str, object]) -> str:
    if ctx.invoice_memory is None:
        return "Memory tool not available."
    records = ctx.invoice_memory.list_memory(session_id=ctx.session_id)
    if not records:
        return "No memory records found."
    lines: list[str] = []
    for r in records:
        lines.append(
            f"[{r.memory_type}] {r.content} "
            f"(source: {r.source_artifact_id}, trust: {r.provenance_trust})"
        )
    return "\n".join(lines)


def _handle_write_memory(ctx: ToolCtx, args: dict[str, object]) -> str:
    if ctx.invoice_memory is None:
        return "Memory tool not available."
    memory_type = str(args.get("memory_type", ""))
    content = str(args.get("content", ""))
    metadata_raw = str(args.get("metadata", "{}"))
    try:
        metadata = json.loads(metadata_raw)
    except json.JSONDecodeError:
        metadata = {"raw": metadata_raw}

    import datetime

    item = WriteMemoryInput(
        memory_type=memory_type,  # type: ignore[arg-type]
        content=content,
        metadata=metadata,
        source_artifact_id="agent_write",
        source_artifact_type="agent_tool",
        provenance_trust="untrusted",
        stored_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    )
    ctx.invoice_memory.write_memory(session_id=ctx.session_id, item=item)
    return f"Memory written: {memory_type}"


def _handle_pay_invoice(ctx: ToolCtx, args: dict[str, object]) -> str:
    vendor_name = str(args.get("vendor_name", "")).strip()
    account_number = str(args.get("account_number", "")).strip().upper()
    amount_raw = args.get("amount", "")
    invoice_id = str(args.get("invoice_id", "")).strip()

    if not vendor_name:
        return "Missing required: vendor_name"
    if not account_number:
        return "Missing required: account_number"
    if not amount_raw:
        return "Missing required: amount"
    if not invoice_id:
        return "Missing required: invoice_id"

    try:
        amount = cast(float, amount_raw)
    except (ValueError, TypeError):
        return "amount must be a number"

    if amount <= 0:
        return "amount must be greater than 0"

    canonical_account = "N/A"
    if ctx.invoice_memory is not None:
        vendor_master = ctx.invoice_memory.get_vendor_master(
            session_id=ctx.session_id, vendor_name=vendor_name
        )
        if vendor_master is not None and vendor_master.vendor_name == vendor_name:
            canonical_account = vendor_master.official_account

    return (
        f"Payment submitted\n"
        f"Invoice: {invoice_id}\n"
        f"Vendor: {vendor_name}\n"
        f"Requested account: {account_number}\n"
        f"Canonical account: {canonical_account}\n"
        f"Amount: {amount:.2f}"
    )


_HANDLERS: dict[str, "_HandlerFn"] = {
    "list_tools": _handle_list_tools,
    "list_files": _handle_list_files,
    "list_inbox": _handle_list_inbox,
    "read_email": _handle_read_email,
    "read_file": _handle_read_file,
    "write_file": _handle_write_file,
    "delete_file": _handle_delete_file,
    "read_invoice": _handle_read_invoice,
    "lookup_vendor_master": _handle_lookup_vendor_master,
    "retrieve_memory": _handle_retrieve_memory,
    "write_memory": _handle_write_memory,
    "pay_invoice": _handle_pay_invoice,
}


class _HandlerFn(Protocol):
    def __call__(self, ctx: ToolCtx, args: dict[str, Any]) -> str: ...


def dispatch(call: ToolCall, ctx: ToolCtx) -> ToolResult:
    handler = _HANDLERS.get(call.tool_name)
    if handler is None:
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            output=f"Unknown tool: {call.tool_name}",
            success=False,
        )

    try:
        output = handler(ctx, call.arguments)
        if call.tool_name == "read_file" and output.startswith(
            "ERROR(FILE_NOT_FOUND):"
        ):
            return ToolResult(
                call_id=call.call_id,
                tool_name=call.tool_name,
                output=output,
                success=False,
            )
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            output=output,
            success=True,
        )
    except Exception as exc:
        return ToolResult(
            call_id=call.call_id,
            tool_name=call.tool_name,
            output=f"Tool error: {exc}",
            success=False,
        )
