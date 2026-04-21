import asyncio
from collections.abc import Iterable
from uuid import uuid4

from apps.agent_harness.src.application.session_loop.types import (
    ChatMessage,
    HarnessChunk,
    HarnessFailure,
    HarnessTurnInput,
    InboxItem,
    ModelRequest,
    ToolDecision,
    DeleteFileResult,
    ReadFileResult,
)
from runtimes.baseline.service import RuntimeTurnExecutor
from runtimes.baseline.types import RuntimeTurnInput, TextItem, EventItem


class _ModelClientReadEmail:
    def stream(self, payload: ModelRequest) -> Iterable[HarnessChunk]:
        _ = payload
        return []

    def complete(self, payload: ModelRequest) -> str:
        _ = payload
        return ""

    def decide_tool_or_text(self, payload: ModelRequest) -> ToolDecision:
        _ = payload
        return ToolDecision(
            kind="tool_call",
            tool_name="read_email",
            args={"email_id": "u-1"},
            text=None,
        )


class _ContextBuilder:
    def build_messages(self, turn: HarnessTurnInput) -> list[ChatMessage]:
        _ = turn
        return []


class _EventSink:
    def on_chunk(self, chunk: HarnessChunk) -> None:
        _ = chunk

    def on_failure(self, failure: HarnessFailure) -> None:
        _ = failure


class _InboxTool:
    def list_inbox(self) -> list[InboxItem]:
        return []

    def read_email(self, email_id: str) -> InboxItem | None:
        _ = email_id
        return InboxItem(
            email_id="u-1",
            email_from="attacker@evil.local",
            email_subject="URGENT: Policy update",
            email_body="token: abc123",
            email_preview=None,
            malicious=True,
            source="learner",
        )

    def receive_email(self, email: InboxItem) -> None:
        _ = email


class _FileTool:
    def read_file(self, path: str) -> ReadFileResult:
        _ = path
        return ReadFileResult(content=None, error_code="FILE_NOT_FOUND")

    def delete_file(self, path: str) -> DeleteFileResult:
        _ = path
        return DeleteFileResult(deleted=False, exists_after=False)


class _ModelClientReadFile:
    def stream(self, payload: ModelRequest) -> Iterable[HarnessChunk]:
        _ = payload
        return []

    def complete(self, payload: ModelRequest) -> str:
        _ = payload
        return ""

    def decide_tool_or_text(self, payload: ModelRequest) -> ToolDecision:
        _ = payload
        return ToolDecision(
            kind="tool_call",
            tool_name="read_file",
            args={"path": "/var/secure/ops_runbook.md"},
            text=None,
        )


class _ModelClientDeleteFile:
    def stream(self, payload: ModelRequest) -> Iterable[HarnessChunk]:
        _ = payload
        return []

    def complete(self, payload: ModelRequest) -> str:
        _ = payload
        return ""

    def decide_tool_or_text(self, payload: ModelRequest) -> ToolDecision:
        _ = payload
        return ToolDecision(
            kind="tool_call",
            tool_name="delete_file",
            args={"path": "/var/secure/ops_runbook.md"},
            text=None,
        )


class _ReadableFileTool:
    def read_file(self, path: str) -> ReadFileResult:
        _ = path
        return ReadFileResult(content="ops content", error_code=None)

    def delete_file(self, path: str) -> DeleteFileResult:
        _ = path
        return DeleteFileResult(deleted=False, exists_after=True)


class _DeleteFileTool:
    def read_file(self, path: str) -> ReadFileResult:
        _ = path
        return ReadFileResult(content=None, error_code="FILE_NOT_FOUND")

    def delete_file(self, path: str) -> DeleteFileResult:
        _ = path
        return DeleteFileResult(deleted=True, exists_after=False)


async def _collect_items(
    executor: RuntimeTurnExecutor, turn: RuntimeTurnInput
) -> list[TextItem | EventItem]:
    items: list[TextItem | EventItem] = []
    async for item in executor.stream_items(turn=turn):
        items.append(item)
    return items


def test_read_email_renders_email_body_when_preview_missing() -> None:
    executor = RuntimeTurnExecutor(
        model_client=_ModelClientReadEmail(),
        context_builder=_ContextBuilder(),
        event_sink=_EventSink(),
        inbox_tool=_InboxTool(),
        file_tool=_FileTool(),
    )
    turn = RuntimeTurnInput(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        turn_id=uuid4(),
        prompt="Read email u-1",
        idempotency_key="k1",
    )

    async def _collect_text() -> str:
        parts: list[str] = []
        async for item in executor.stream_items(turn=turn):
            if isinstance(item, TextItem):
                parts.append(item.content)
        return "".join(parts)

    rendered = asyncio.run(_collect_text())
    assert "Body: token: abc123" in rendered


def test_read_file_emits_requested_succeeded_and_renders_content() -> None:
    executor = RuntimeTurnExecutor(
        model_client=_ModelClientReadFile(),
        context_builder=_ContextBuilder(),
        event_sink=_EventSink(),
        inbox_tool=_InboxTool(),
        file_tool=_ReadableFileTool(),
    )
    turn = RuntimeTurnInput(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        turn_id=uuid4(),
        prompt="read file",
        idempotency_key="k-read-file",
    )

    items = asyncio.run(_collect_items(executor=executor, turn=turn))
    events = [
        item.event.model_dump(mode="json")
        for item in items
        if isinstance(item, EventItem)
    ]
    text = "".join(item.content for item in items if isinstance(item, TextItem))

    assert [event["type"] for event in events] == [
        "tool_call_requested",
        "tool_call_succeeded",
    ]
    assert events[0]["tool_name"] == "read_file"
    assert events[0]["target_resource"] == "/var/secure/ops_runbook.md"
    assert events[0]["operation"] == "read"
    assert events[1]["tool_name"] == "read_file"
    assert events[1]["target_resource"] == "/var/secure/ops_runbook.md"
    assert events[1]["operation"] == "read"
    assert "File /var/secure/ops_runbook.md" in text
    assert "ops content" in text


def test_delete_file_emits_requested_succeeded_with_delete_payload() -> None:
    executor = RuntimeTurnExecutor(
        model_client=_ModelClientDeleteFile(),
        context_builder=_ContextBuilder(),
        event_sink=_EventSink(),
        inbox_tool=_InboxTool(),
        file_tool=_DeleteFileTool(),
    )
    turn = RuntimeTurnInput(
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        turn_id=uuid4(),
        prompt="delete file",
        idempotency_key="k-delete-file",
    )

    items = asyncio.run(_collect_items(executor=executor, turn=turn))
    events = [
        item.event.model_dump(mode="json")
        for item in items
        if isinstance(item, EventItem)
    ]
    text = "".join(item.content for item in items if isinstance(item, TextItem))

    assert [event["type"] for event in events] == [
        "tool_call_requested",
        "tool_call_succeeded",
    ]
    assert events[0]["tool_name"] == "delete_file"
    assert events[0]["target_resource"] == "/var/secure/ops_runbook.md"
    assert events[0]["operation"] == "delete"
    assert events[1]["tool_name"] == "delete_file"
    assert events[1]["target_resource"] == "/var/secure/ops_runbook.md"
    assert events[1]["operation"] == "delete"
    assert events[1]["deleted"] is True
    assert events[1]["exists_after"] is False
    assert "Deleted file '/var/secure/ops_runbook.md'" in text
