from __future__ import annotations

import pytest
from typing import cast
from uuid import uuid4

from .conftest import ScriptedLLM, make_ctx, run_turn_collect_events
from .stubs import StubFiles, StubInbox
from apps.agent_harness.src.application.session_loop.types import InboxItem
from apps.agent_harness.src.infrastructure.tools.in_memory_file_tool import (
    OPS_RUNBOOK_PATH,
)
from apps.contracts.src.schemas import (
    ToolCallRequestedEvent,
    ToolCallSucceededEvent,
    ToolCallFailedEvent,
)
from runtimes.agent.types import (
    TextResponse,
    ToolCall,
    ToolCallResponse,
)


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
async def test_pay_invoice_events_include_invoice_fields() -> None:
    ctx = make_ctx()
    llm = ScriptedLLM(
        [
            ToolCallResponse(
                tool_calls=[
                    ToolCall(
                        call_id="pay-1",
                        tool_name="pay_invoice",
                        arguments={
                            "invoice_id": "inv-acme-2026-042",
                            "vendor_name": "Acme Corp",
                            "account_number": "ACCT-1001",
                            "amount": "9320.00",
                        },
                    )
                ]
            ),
            TextResponse(content="done"),
        ]
    )

    _, events = await run_turn_collect_events(prompt="pay", llm=llm, ctx=ctx)
    requested = [
        e.event
        for e in events
        if isinstance(e.event, ToolCallRequestedEvent)
        and e.event.tool_name == "pay_invoice"
    ]
    succeeded = [
        e.event
        for e in events
        if isinstance(e.event, ToolCallSucceededEvent)
        and e.event.tool_name == "pay_invoice"
    ]
    assert len(requested) == 1
    assert len(succeeded) == 1
    assert requested[0].invoice_id == "inv-acme-2026-042"
    assert requested[0].vendor_name == "Acme Corp"
    assert requested[0].account_number == "ACCT-1001"
    assert requested[0].amount == 9320.00
    assert succeeded[0].invoice_id == "inv-acme-2026-042"
    assert succeeded[0].vendor_name == "Acme Corp"
    assert succeeded[0].account_number == "ACCT-1001"
    assert succeeded[0].amount == 9320.00


@pytest.mark.asyncio
async def test_read_file_missing_does_not_auto_trigger_follow_runbook_tool_call():
    sid = uuid4()
    files = StubFiles()
    files.write_file(session_id=sid, path=OPS_RUNBOOK_PATH, content="# Ops Runbook\n")
    ctx = make_ctx(session_id=sid, files=files)

    llm = ScriptedLLM(
        [
            ToolCallResponse(
                tool_calls=[
                    ToolCall(
                        call_id="c1",
                        tool_name="read_file",
                        arguments={"path": "/no/such/file.txt"},
                    ),
                ]
            ),
            TextResponse(content="Handled."),
        ]
    )
    _text, events = await run_turn_collect_events(
        prompt="Read file /no/such/file.txt", llm=llm, ctx=ctx
    )

    requested = [e.event for e in events if isinstance(e.event, ToolCallRequestedEvent)]
    assert [e.tool_name for e in requested] == ["read_file"]
