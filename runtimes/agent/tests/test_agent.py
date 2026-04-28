from __future__ import annotations

import pytest
from typing import cast

from .conftest import ScriptedLLM, make_ctx, run_turn, run_turn_collect_events
from .stubs import StubFiles, StubInbox, StubInvoiceMemory
from runtimes.agent.types import TextResponse, ToolCall, ToolCallResponse
from runtimes.agent.tools import TOOLS, dispatch, ToolCtx

from apps.agent_harness.src.application.session_loop.types import (
    InboxItem,
    VendorMasterRecord,
)
from apps.contracts.src.schemas import (
    ToolCallRequestedEvent,
    ToolCallSucceededEvent,
    ToolCallFailedEvent,
)
from uuid import uuid4


@pytest.mark.asyncio
async def test_text_response_immediately():
    llm = ScriptedLLM([TextResponse(content="Hello! How can I help?")])
    result = await run_turn(prompt="hi", llm=llm)

    assert result == "Hello! How can I help?"
    assert len(llm.calls) == 1
    assert llm.calls[0][0].role == "system"
    assert llm.calls[0][1].role == "user"
    assert llm.calls[0][1].content == "hi"


@pytest.mark.asyncio
async def test_single_tool_call_then_text(ctx: ToolCtx, stub_inbox: StubInbox):
    # Setup data using the injected stub_inbox
    stub_inbox.receive_email(
        InboxItem(
            email_id="e1",
            email_from="alice@example.com",
            email_subject="Welcome",
            email_body="Hello and welcome!",
        )
    )

    # Setup the LLM
    llm = ScriptedLLM(
        [
            ToolCallResponse(
                tool_calls=[
                    ToolCall(call_id="c1", tool_name="list_inbox", arguments={}),
                ]
            ),
            TextResponse(content="You have 1 email from alice@example.com."),
        ]
    )

    # Run the turn using the injected ctx
    result = await run_turn(prompt="check my inbox", llm=llm, ctx=ctx)

    # Assertions
    assert "alice@example.com" in result
    assert len(llm.calls) == 2

    tool_msg = llm.calls[1][-1]
    assert tool_msg.role == "tool"
    assert "alice@example.com" in tool_msg.content


@pytest.mark.asyncio
async def test_single_tool_call_then_text_manual_ctx():
    inbox = StubInbox()
    inbox.receive_email(
        InboxItem(
            email_id="e1",
            email_from="alice@example.com",
            email_subject="Welcome",
            email_body="Hello and welcome!",
        )
    )

    ctx = make_ctx(inbox=inbox)

    llm = ScriptedLLM(
        [
            ToolCallResponse(
                tool_calls=[
                    ToolCall(call_id="c1", tool_name="list_inbox", arguments={}),
                ]
            ),
            TextResponse(content="You have 1 email from alice@example.com."),
        ]
    )

    result = await run_turn(prompt="check my inbox", llm=llm, ctx=ctx)

    assert "alice@example.com" in result
    assert len(llm.calls) == 2

    tool_msg = llm.calls[1][-1]
    assert tool_msg.role == "tool"
    assert "alice@example.com" in tool_msg.content


@pytest.mark.asyncio
async def test_multiple_tool_calls_in_one_turn():
    files = StubFiles()
    files.write_file(
        session_id=uuid4(), path="/etc/hosts", content="127.0.0.1 localhost"
    )

    ctx = make_ctx(files=files)

    llm = ScriptedLLM(
        [
            ToolCallResponse(
                tool_calls=[
                    ToolCall(
                        call_id="c1",
                        tool_name="read_file",
                        arguments={"path": "/etc/hosts"},
                    ),
                    ToolCall(call_id="c2", tool_name="list_tools", arguments={}),
                ]
            ),
            TextResponse(content="Done processing."),
        ]
    )

    result = await run_turn(prompt="read hosts and list tools", llm=llm, ctx=ctx)
    assert result == "Done processing."
    assert len(llm.calls) == 2

    tool_messages = [m for m in llm.calls[1] if m.role == "tool"]
    assert len(tool_messages) == 2


@pytest.mark.asyncio
async def test_multi_step_agent_loop():
    inbox = StubInbox()
    inbox.receive_email(
        InboxItem(
            email_id="e1",
            email_from="boss@corp.com",
            email_subject="Read the file",
            email_body="Please read /tmp/notes.txt",
        )
    )

    files = StubFiles()
    files.write_file(
        session_id=uuid4(), path="/tmp/notes.txt", content="Meeting at 3pm"
    )

    ctx = make_ctx(inbox=inbox, files=files)

    llm = ScriptedLLM(
        [
            ToolCallResponse(
                tool_calls=[
                    ToolCall(call_id="c1", tool_name="list_inbox", arguments={}),
                ]
            ),
            ToolCallResponse(
                tool_calls=[
                    ToolCall(
                        call_id="c2",
                        tool_name="read_email",
                        arguments={"email_id": "e1"},
                    ),
                ]
            ),
            ToolCallResponse(
                tool_calls=[
                    ToolCall(
                        call_id="c3",
                        tool_name="read_file",
                        arguments={"path": "/tmp/notes.txt"},
                    ),
                ]
            ),
            TextResponse(content="The file says: Meeting at 3pm"),
        ]
    )

    result = await run_turn(
        prompt="check inbox and follow instructions", llm=llm, ctx=ctx
    )

    assert "Meeting at 3pm" in result
    assert len(llm.calls) == 4


@pytest.mark.asyncio
async def test_unknown_tool_returns_error():
    ctx = make_ctx()

    llm = ScriptedLLM(
        [
            ToolCallResponse(
                tool_calls=[
                    ToolCall(call_id="c1", tool_name="nonexistent_tool", arguments={}),
                ]
            ),
            TextResponse(content="That tool doesn't exist."),
        ]
    )

    result = await run_turn(prompt="try a fake tool", llm=llm, ctx=ctx)
    assert "doesn't exist" in result

    tool_msg = llm.calls[1][-1]
    assert "Unknown tool" in tool_msg.content


@pytest.mark.asyncio
async def test_max_iterations():
    ctx = make_ctx()

    infinite_tools = [
        ToolCallResponse(
            tool_calls=[
                ToolCall(call_id=f"c{i}", tool_name="list_tools", arguments={}),
            ]
        )
        for i in range(20)
    ]

    llm = ScriptedLLM(infinite_tools)
    result = await run_turn(prompt="keep going", llm=llm, ctx=ctx)

    assert "maximum number of steps" in result.lower()


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
async def test_read_file_not_found():
    ctx = make_ctx()
    result = dispatch(
        ToolCall(call_id="c1", tool_name="read_file", arguments={"path": "/nope"}), ctx
    )

    assert result.success
    assert "not found" in result.output.lower()


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
async def test_empty_text_response_yields_nothing():
    llm = ScriptedLLM([TextResponse(content="")])
    result = await run_turn(prompt="hi", llm=llm)
    assert result == ""


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
    assert "not found" in read.output.lower() or "File not found" in read.output


@pytest.mark.asyncio
async def test_tool_call_emits_requested_and_succeeded_events():
    inbox = StubInbox()
    inbox.receive_email(
        InboxItem(
            email_id="e1",
            email_from="alice@example.com",
            email_subject="Hello",
            email_body="Body text",
        )
    )

    ctx = make_ctx(inbox=inbox)
    llm = ScriptedLLM(
        [
            ToolCallResponse(
                tool_calls=[
                    ToolCall(call_id="c1", tool_name="list_inbox", arguments={}),
                ]
            ),
            TextResponse(content="Done."),
        ]
    )

    text, events = await run_turn_collect_events(prompt="check inbox", llm=llm, ctx=ctx)

    assert text == "Done."

    requested = [e for e in events if isinstance(e.event, ToolCallRequestedEvent)]
    succeeded = [e for e in events if isinstance(e.event, ToolCallSucceededEvent)]
    failed = [e for e in events if isinstance(e.event, ToolCallFailedEvent)]

    assert len(requested) == 1
    requested_event = cast(ToolCallRequestedEvent, requested[0].event)
    assert requested_event.tool_name == "list_inbox"
    assert len(succeeded) == 1
    succeeded_event = cast(ToolCallSucceededEvent, succeeded[0].event)
    assert succeeded_event.tool_name == "list_inbox"
    assert len(failed) == 0


@pytest.mark.asyncio
async def test_unknown_tool_emits_failed_event():
    ctx = make_ctx()
    llm = ScriptedLLM(
        [
            ToolCallResponse(
                tool_calls=[
                    ToolCall(call_id="c1", tool_name="nonexistent_tool", arguments={}),
                ]
            ),
            TextResponse(content="Handled."),
        ]
    )

    text, events = await run_turn_collect_events(prompt="try fake", llm=llm, ctx=ctx)

    assert text == "Handled."

    requested = [e for e in events if isinstance(e.event, ToolCallRequestedEvent)]
    failed = [e for e in events if isinstance(e.event, ToolCallFailedEvent)]

    assert len(requested) == 1
    requested_event = cast(ToolCallRequestedEvent, requested[0].event)
    assert requested_event.tool_name == "nonexistent_tool"
    assert len(failed) == 1
    failed_event = cast(ToolCallFailedEvent, failed[0].event)
    assert failed_event.tool_name == "nonexistent_tool"
    assert failed_event.error_code == "TOOL_ERROR"


@pytest.mark.asyncio
async def test_multi_tool_call_emits_events_per_tool():
    files = StubFiles()
    files.write_file(session_id=uuid4(), path="/tmp/test.txt", content="hello")

    ctx = make_ctx(files=files)
    llm = ScriptedLLM(
        [
            ToolCallResponse(
                tool_calls=[
                    ToolCall(
                        call_id="c1",
                        tool_name="read_file",
                        arguments={"path": "/tmp/test.txt"},
                    ),
                    ToolCall(call_id="c2", tool_name="list_tools", arguments={}),
                ]
            ),
            TextResponse(content="All done."),
        ]
    )

    text, events = await run_turn_collect_events(prompt="do stuff", llm=llm, ctx=ctx)

    assert text == "All done."

    requested = [e for e in events if isinstance(e.event, ToolCallRequestedEvent)]
    succeeded = [e for e in events if isinstance(e.event, ToolCallSucceededEvent)]

    assert len(requested) == 2
    assert len(succeeded) == 2
    requested_events = [cast(ToolCallRequestedEvent, e.event) for e in requested]
    assert [e.tool_name for e in requested_events] == ["read_file", "list_tools"]


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
