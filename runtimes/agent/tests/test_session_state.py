from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest

from apps.agent_harness.src.application.session_loop.types import InboxItem
from apps.agent_harness.src.infrastructure.tools.in_memory_file_tool import (
    OPS_RUNBOOK_PATH,
)
from runtimes.agent.session_state import (
    EphemeralRuntimeSessionState,
    RuntimeSessionMismatchError,
)
from runtimes.agent.hooks import NullAgentLabHooks
from runtimes.agent.types import ChatMessage


def test_expected_session_rejects_cross_session_access() -> None:
    owning_session_id = uuid4()
    state = EphemeralRuntimeSessionState(expected_session_id=owning_session_id)

    state.ensure_session(owning_session_id)

    with pytest.raises(RuntimeSessionMismatchError):
        state.ensure_session(uuid4())


def test_local_runtime_binds_to_first_session() -> None:
    state = EphemeralRuntimeSessionState()
    session_id = uuid4()

    state.ensure_session(session_id)

    assert state.session_id == session_id
    with pytest.raises(RuntimeSessionMismatchError):
        state.ensure_session(uuid4())


def test_transcript_is_bounded_and_returned_as_a_snapshot() -> None:
    session_id = uuid4()
    state = EphemeralRuntimeSessionState(
        expected_session_id=session_id,
        max_transcript_messages=2,
    )

    state.append_transcript(session_id, ChatMessage(role="user", content="one"))
    state.append_transcript(session_id, ChatMessage(role="assistant", content="two"))
    state.append_transcript(session_id, ChatMessage(role="user", content="three"))
    snapshot = state.transcript_snapshot(session_id)
    snapshot.clear()

    assert [message.content for message in state.transcript_snapshot(session_id)] == [
        "two",
        "three",
    ]


def test_clear_discards_all_ephemeral_session_data() -> None:
    session_id = uuid4()
    state = EphemeralRuntimeSessionState(expected_session_id=session_id)
    state.append_transcript(session_id, ChatMessage(role="user", content="hello"))
    state.inbox.receive_email(
        InboxItem(
            email_id="e2",
            email_from="ops@example.com",
            email_subject="Test",
            email_body="Body",
        )
    )
    state.files.write_file(
        session_id=session_id,
        path=OPS_RUNBOOK_PATH,
        content="temporary",
    )
    state.invoice_memory.seed_session_state(session_id=session_id)
    lab_id = uuid4()
    original_hooks = state.get_or_create_lab_hooks(lab_id, NullAgentLabHooks)
    state.mark_seeded(session_id)

    state.clear()

    assert state.transcript_snapshot(session_id) == []
    assert [item.email_id for item in state.inbox.list_inbox()] == ["e1"]
    assert (
        state.files.read_file(
            session_id=session_id,
            path=OPS_RUNBOOK_PATH,
        ).content
        is None
    )
    assert (
        state.invoice_memory.get_vendor_master(
            session_id=session_id,
            vendor_name="Acme Corp",
        )
        is None
    )
    assert state.is_seeded(session_id) is False
    assert (
        state.get_or_create_lab_hooks(lab_id, NullAgentLabHooks) is not original_hooks
    )


def test_lab_hooks_are_reused_for_the_runtime_session() -> None:
    state = EphemeralRuntimeSessionState(expected_session_id=uuid4())
    lab_id = uuid4()

    first = state.get_or_create_lab_hooks(lab_id, NullAgentLabHooks)
    second = state.get_or_create_lab_hooks(lab_id, NullAgentLabHooks)

    assert first is second


def test_inbox_assigns_unique_ids_as_part_of_the_locked_append() -> None:
    state = EphemeralRuntimeSessionState(expected_session_id=uuid4())
    email = InboxItem(
        email_id="",
        email_from="ops@example.com",
        email_subject="Test",
        email_body="Body",
    )

    first_id = state.inbox.receive_email_assigning_id(email)
    second_id = state.inbox.receive_email_assigning_id(email)

    assert (first_id, second_id) == ("e2", "e3")
    assert [item.email_id for item in state.inbox.list_inbox()] == [
        "e1",
        "e2",
        "e3",
    ]


@pytest.mark.asyncio
async def test_turns_are_serialized() -> None:
    session_id = uuid4()
    state = EphemeralRuntimeSessionState(expected_session_id=session_id)
    first_entered = asyncio.Event()
    release_first = asyncio.Event()
    order: list[str] = []

    async def first_turn() -> None:
        async with state.turn(session_id):
            order.append("first-entered")
            first_entered.set()
            await release_first.wait()
            order.append("first-exited")

    async def second_turn() -> None:
        await first_entered.wait()
        async with state.turn(session_id):
            order.append("second-entered")

    first_task = asyncio.create_task(first_turn())
    second_task = asyncio.create_task(second_turn())
    await first_entered.wait()
    await asyncio.sleep(0)

    assert order == ["first-entered"]

    release_first.set()
    await asyncio.gather(first_task, second_task)

    assert order == ["first-entered", "first-exited", "second-entered"]
