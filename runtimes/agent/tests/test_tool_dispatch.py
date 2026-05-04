from __future__ import annotations

import pytest
from typing import cast
from uuid import uuid4

from .conftest import make_ctx
from .stubs import StubFiles, StubInbox, StubInvoiceMemory
from apps.agent_harness.src.application.session_loop.types import (
    InboxItem,
    VendorMasterRecord,
)
from runtimes.agent.types import ToolCall
from runtimes.agent.tools import TOOLS, dispatch, filter_tools


@pytest.mark.asyncio
async def test_read_email_tool():
    inbox = StubInbox()
    inbox.receive_email(
        InboxItem(
            email_id="e1",
            email_from="bob@example.com",
            email_subject="Hello",
            email_body="This is the body.",
        )
    )

    ctx = make_ctx(inbox=inbox)
    result = dispatch(
        ToolCall(call_id="c1", tool_name="read_email", arguments={"email_id": "e1"}),
        ctx,
    )

    assert result.success
    assert "bob@example.com" in result.output
    assert "This is the body." in result.output


@pytest.mark.asyncio
async def test_list_tools_respects_ctx_available_tools():
    allowed = tuple(filter_tools(("list_tools", "list_inbox", "read_email")))
    ctx = make_ctx(available_tools=allowed)
    result = dispatch(
        ToolCall(call_id="c1", tool_name="list_tools", arguments={}),
        ctx,
    )

    assert result.success
    assert result.output.startswith("<ul>")
    assert "<strong>list_tools</strong>:" in result.output
    assert "<strong>list_inbox</strong>:" in result.output
    assert "<strong>read_email</strong>:" in result.output
    assert "<strong>delete_file</strong>:" not in result.output
    assert "<strong>pay_invoice</strong>:" not in result.output


@pytest.mark.asyncio
async def test_read_file_not_found():
    ctx = make_ctx()
    result = dispatch(
        ToolCall(call_id="c1", tool_name="read_file", arguments={"path": "/nope"}), ctx
    )

    assert not result.success
    assert "FILE_NOT_FOUND" in result.output


@pytest.mark.asyncio
async def test_list_files_returns_sorted_paths():
    sid = uuid4()
    files = StubFiles()
    files.write_file(session_id=sid, path="/z-last.txt", content="z")
    files.write_file(session_id=sid, path="/a-first.txt", content="a")
    ctx = make_ctx(session_id=sid, files=files)

    result = dispatch(
        ToolCall(call_id="c1", tool_name="list_files", arguments={}),
        ctx,
    )

    assert result.success
    assert result.output == "<ul>\n<li>/a-first.txt</li>\n<li>/z-last.txt</li>\n</ul>"


@pytest.mark.asyncio
async def test_write_then_read_file():
    sid = uuid4()
    files = StubFiles()
    ctx = make_ctx(session_id=sid, files=files)

    write_result = dispatch(
        ToolCall(
            call_id="c1",
            tool_name="write_file",
            arguments={"path": "/tmp/test.txt", "content": "hello world"},
        ),
        ctx,
    )
    assert write_result.success

    read_result = dispatch(
        ToolCall(
            call_id="c2",
            tool_name="read_file",
            arguments={"path": "/tmp/test.txt"},
        ),
        ctx,
    )
    assert read_result.success
    assert "hello world" in read_result.output


@pytest.mark.asyncio
async def test_vendor_lookup():
    invoice = StubInvoiceMemory()
    invoice.add_vendor(
        VendorMasterRecord(
            vendor_id="v1",
            vendor_name="Acme Corp",
            official_account="1234567890",
            routing_number="021000021",
            status="active",
            last_verified="2025-01-01",
        )
    )

    ctx = make_ctx(invoice=invoice)
    result = dispatch(
        ToolCall(
            call_id="c1",
            tool_name="lookup_vendor_master",
            arguments={"vendor_name": "Acme Corp"},
        ),
        ctx,
    )

    assert result.success
    assert "Acme Corp" in result.output
    assert "1234567890" in result.output


@pytest.mark.asyncio
async def test_all_tool_definitions_are_valid():
    for t in TOOLS:
        openai = t.to_openai_tool()
        assert isinstance(openai, dict)
        assert openai["type"] == "function"
        func = cast(dict[str, object], openai["function"])
        assert isinstance(func["name"], str)
        assert isinstance(func["description"], str)
        assert isinstance(func["parameters"], dict)


@pytest.mark.asyncio
async def test_delete_file():
    sid = uuid4()
    files = StubFiles()
    files.write_file(session_id=sid, path="/tmp/killme.txt", content="bye")
    ctx = make_ctx(session_id=sid, files=files)

    result = dispatch(
        ToolCall(
            call_id="c1",
            tool_name="delete_file",
            arguments={"path": "/tmp/killme.txt"},
        ),
        ctx,
    )
    assert result.success
    assert "Deleted" in result.output

    read = dispatch(
        ToolCall(
            call_id="c2",
            tool_name="read_file",
            arguments={"path": "/tmp/killme.txt"},
        ),
        ctx,
    )
    assert "ERROR(FILE_NOT_FOUND): /tmp/killme.txt" == read.output


@pytest.mark.asyncio
async def test_extract_target_resource():
    from runtimes.agent.agent import extract_target, extract_operation

    tc = ToolCall(call_id="c1", tool_name="read_email", arguments={"email_id": "e1"})
    assert extract_target(tc) == "e1"
    assert extract_operation(tc) == "read"

    tc2 = ToolCall(
        call_id="c2",
        tool_name="write_file",
        arguments={"path": "/tmp/x.txt", "content": "hi"},
    )
    assert extract_target(tc2) == "/tmp/x.txt"
    assert extract_operation(tc2) == "write"

    tc3 = ToolCall(call_id="c3", tool_name="list_tools", arguments={})
    assert extract_target(tc3) is None
    assert extract_operation(tc3) == "list"
