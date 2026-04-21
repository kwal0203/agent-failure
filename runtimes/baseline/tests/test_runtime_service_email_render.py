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
from runtimes.baseline.types import RuntimeTurnInput, TextItem


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
