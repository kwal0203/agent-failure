from __future__ import annotations

import pytest
from uuid import uuid4

from .conftest import ScriptedLLM, make_ctx, run_turn
from .stubs import StubFiles, StubInbox
from apps.agent_harness.src.application.session_loop.types import InboxItem
from runtimes.agent.types import (
    ChatMessage,
    TextResponse,
    ToolCall,
    ToolCallResponse,
)
from runtimes.agent.tools import ToolCtx


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
async def test_prior_messages_are_replayed_into_turn_context():
    llm = ScriptedLLM([TextResponse(content="Acknowledged.")])
    result = await run_turn(
        prompt="current prompt",
        llm=llm,
        prior_messages=[
            ChatMessage(role="user", content="earlier question"),
            ChatMessage(role="assistant", content="earlier answer"),
        ],
    )
    assert result == "Acknowledged."
    assert len(llm.calls) == 1
    call = llm.calls[0]
    assert [m.role for m in call[:4]] == ["system", "user", "assistant", "user"]
    assert call[1].content == "earlier question"
    assert call[2].content == "earlier answer"
    assert call[3].content == "current prompt"


@pytest.mark.asyncio
async def test_single_tool_call_then_text(ctx: ToolCtx, stub_inbox: StubInbox):
    stub_inbox.receive_email(
        InboxItem(
            email_id="e1",
            email_from="alice@example.com",
            email_subject="Welcome",
            email_body="Hello and welcome!",
        )
    )

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
async def test_empty_text_response_yields_nothing():
    llm = ScriptedLLM([TextResponse(content="")])
    result = await run_turn(prompt="hi", llm=llm)
    assert result == ""


@pytest.mark.asyncio
async def test_run_turn_allows_model_response_after_read_file_tool():
    sid = uuid4()
    files = StubFiles()
    files.write_file(
        session_id=sid, path="/tmp/runbook.md", content="RAW RUNBOOK CONTENT"
    )
    ctx = make_ctx(session_id=sid, files=files)

    llm = ScriptedLLM(
        [
            ToolCallResponse(
                tool_calls=[
                    ToolCall(
                        call_id="c1",
                        tool_name="read_file",
                        arguments={"path": "/tmp/runbook.md"},
                    )
                ]
            ),
            TextResponse(content="Paraphrased summary emitted by model."),
        ]
    )

    text = await run_turn(prompt="Read file /tmp/runbook.md", llm=llm, ctx=ctx)
    assert text == "Paraphrased summary emitted by model."
    assert len(llm.calls) == 2
