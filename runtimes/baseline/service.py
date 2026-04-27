from collections.abc import AsyncIterator
from time import monotonic
from apps.contracts.src.schemas import (
    TurnStartedEvent,
    TextChunkEvent,
    TurnCompletedEvent,
    RuntimeStreamEvent,
    TurnFailedEvent,
)
from apps.agent_harness.src.application.session_loop.ports import (
    ModelClientPort,
    LabContextBuilderPort,
    EventSinkPort,
    InboxToolPort,
    FileToolPort,
    InvoiceMemoryToolPort,
)
from apps.agent_harness.src.application.session_loop.types import (
    ModelRequest,
    ChatMessage,
    HarnessTurnInput,
    InboxItem,
    ToolDecision,
)

from .types import RuntimeTurnInput, RuntimeExecutorItem, EventItem, TextItem
from .handlers import (
    TurnContext,
    ToolHandler,
    ListToolsHandler,
    ListInboxHandler,
    ReadEmailHandler,
    ReadFileHandler,
    WriteFileHandler,
    DeleteFileHandler,
    ReadInvoiceHandler,
    LookupVendorMasterHandler,
    RetrieveMemoryHandler,
    WriteMemoryHandler,
)
from .labs import LabHooks, NullLabHooks

from uuid import UUID


class RuntimeTurnExecutor:
    def __init__(
        self,
        *,
        model_client: ModelClientPort,
        context_builder: LabContextBuilderPort,
        event_sink: EventSinkPort,
        inbox_tool: InboxToolPort,
        file_tool: FileToolPort,
        invoice_memory_tool: InvoiceMemoryToolPort | None = None,
        hooks: LabHooks | None = None,
    ) -> None:
        self._model_client = model_client
        self._context_builder = context_builder
        self._event_sink = event_sink
        self._inbox_tool = inbox_tool
        self._file_tool = file_tool
        self._invoice_memory_tool = invoice_memory_tool
        self._hooks = hooks if hooks is not None else NullLabHooks()
        self._attack_seeded_sessions: set[UUID] = set()
        self._urgent_malicious_context_by_session: dict[UUID, str] = {}
        self._lab2_destructive_runbook_by_session: dict[UUID, bool] = {}
        self._lab2_autonomous_delete_applied_sessions: set[UUID] = set()
        self._handlers: dict[str, ToolHandler] = {
            "list_tools": ListToolsHandler(),
            "list_inbox": ListInboxHandler(),
            "read_email": ReadEmailHandler(),
            "read_file": ReadFileHandler(),
            "write_file": WriteFileHandler(),
            "delete_file": DeleteFileHandler(),
            "read_invoice": ReadInvoiceHandler(),
            "lookup_vendor_master": LookupVendorMasterHandler(),
            "retrieve_memory": RetrieveMemoryHandler(),
            "write_memory": WriteMemoryHandler(),
        }
        self._handlers.update(self._hooks.get_handlers())

    def _build_turn_context(self, turn: RuntimeTurnInput) -> TurnContext:
        return TurnContext(
            turn=turn,
            inbox_tool=self._inbox_tool,
            file_tool=self._file_tool,
            invoice_memory_tool=self._invoice_memory_tool,
            attack_seeded_sessions=self._attack_seeded_sessions,
            urgent_malicious_context_by_session=self._urgent_malicious_context_by_session,
            lab2_destructive_runbook_by_session=self._lab2_destructive_runbook_by_session,
            lab2_autonomous_delete_applied_sessions=self._lab2_autonomous_delete_applied_sessions,
            hooks=self._hooks,
        )

    def _chunk_text(self, text: str, chunk_size: int = 24) -> list[str]:
        if not text:
            return [""]
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    def _emit_text_chunks(
        self,
        *,
        text: str,
        full_text_so_far: str,
        token_disclosed_emitted: bool,
    ) -> tuple[list[RuntimeExecutorItem], str, bool]:
        items: list[RuntimeExecutorItem] = []
        for part in self._chunk_text(text):
            full_text_so_far += part
            evt = self._hooks.maybe_emit_token_disclosed(
                text=full_text_so_far,
                emitted=token_disclosed_emitted,
            )
            if evt is not None:
                items.append(evt)
                token_disclosed_emitted = True
            items.append(TextItem(content=part))
        return items, full_text_so_far, token_disclosed_emitted

    def _emit_text_items(
        self,
        items: list[RuntimeExecutorItem],
        *,
        full_text_so_far: str,
        token_disclosed_emitted: bool,
    ) -> tuple[list[RuntimeExecutorItem], str, bool]:
        result: list[RuntimeExecutorItem] = []
        for item in items:
            if isinstance(item, EventItem):
                result.append(item)
            else:
                text_items, full_text_so_far, token_disclosed_emitted = (
                    self._emit_text_chunks(
                        text=item.content,
                        full_text_so_far=full_text_so_far,
                        token_disclosed_emitted=token_disclosed_emitted,
                    )
                )
                result.extend(text_items)
        return result, full_text_so_far, token_disclosed_emitted

    def _decide_tool_or_text(self, turn: RuntimeTurnInput) -> ToolDecision:
        user_prompt = turn.prompt.strip()
        messages: list[ChatMessage] = [
            ChatMessage(
                role="system",
                content=(
                    "You are a routing classifier. Decide whether to call a tool.\n"
                    "Return JSON only with schema:\n"
                    '{"kind":"tool_call|text","tool_name":"list_tools|list_inbox|read_email|read_file|write_file|delete_file|read_invoice|lookup_vendor_master|retrieve_memory|write_memory|pay_invoice|null","args":{},"text":null|string}\n'
                    'When tool_name is "list_tools", args must be {}.\n'
                    'When tool_name is "read_email", args must include {"email_id":"..."}.\n'
                    'When tool_name is "read_file" or "delete_file", args must include {"path":"..."}.\n'
                    'When tool_name is "write_file", args must include {"path":"...","content":"..."}.\n'
                    'When tool_name is "read_invoice", args must include {"invoice_id":"..."}.\n'
                    'When tool_name is "lookup_vendor_master", args must include {"vendor_name":"..."}.\n'
                    'When tool_name is "retrieve_memory", args must include {"query":"..."}.\n'
                    'When tool_name is "write_memory", args must include {"memory_type":"...","content":"...","metadata":"..."}.\n'
                    'When tool_name is "pay_invoice", args must include {"vendor_name":"...","account_number":"...","amount":"...","invoice_id":"..."}.\n'
                    "Use tool_call only when tool output is needed."
                ),
            ),
            ChatMessage(role="user", content=user_prompt),
        ]

        decision = self._model_client.decide_tool_or_text(
            payload=ModelRequest(messages=messages)
        )
        if decision.kind == "tool_call":
            return ToolDecision(
                kind="tool_call",
                tool_name=decision.tool_name,
                args=decision.args,
                text=None,
            )

        return ToolDecision(
            kind="text",
            tool_name=None,
            args={},
            text=decision.text
            if isinstance(decision.text, str) and decision.text.strip()
            else None,
        )

    async def stream_items(
        self, turn: RuntimeTurnInput
    ) -> AsyncIterator[RuntimeExecutorItem]:
        token_disclosed_emitted = False
        full_text_so_far = ""
        self._hooks.seed_artifacts(turn, self._file_tool, self._invoice_memory_tool)
        ctx = self._build_turn_context(turn)

        tool_call_decision = self._decide_tool_or_text(turn=turn)
        pre = self._hooks.pre_dispatch(
            ctx,
            tool_call_decision,
            full_text_so_far,
            token_disclosed_emitted,
        )
        if pre is not None:
            for item in pre.items:
                yield item
            return

        if tool_call_decision.kind == "tool_call":
            tool_name = tool_call_decision.tool_name
            if tool_name is not None and tool_name in self._handlers:
                handler = self._handlers[tool_name]
                items, _, _ = self._emit_text_items(
                    handler.handle(tool_call_decision, ctx),
                    full_text_so_far=full_text_so_far,
                    token_disclosed_emitted=token_disclosed_emitted,
                )
                for item in items:
                    yield item
            return

        harness_turn = HarnessTurnInput(
            session_id=turn.session_id,
            lab_id=turn.lab_id,
            lab_version_id=turn.lab_version_id,
            prompt=turn.prompt,
        )
        messages = self._context_builder.build_messages(turn=harness_turn)
        request = ModelRequest(messages=messages)

        for chunk in self._model_client.stream(payload=request):
            self._event_sink.on_chunk(chunk=chunk)
            full_text_so_far += chunk.content
            evt = self._hooks.maybe_emit_token_disclosed(
                text=full_text_so_far,
                emitted=token_disclosed_emitted,
            )
            if evt is not None:
                yield evt
                token_disclosed_emitted = True
                yield TextItem(content=chunk.content)
                continue

            yield TextItem(content=chunk.content)

    def inject_email_into_inbox(self, inbox_item: InboxItem) -> None:
        self._inbox_tool.receive_email(email=inbox_item)


async def stream_turn_events(
    input: RuntimeTurnInput,
    executor: RuntimeTurnExecutor,
) -> AsyncIterator[RuntimeStreamEvent]:
    start = monotonic()
    chunks_emitted = 0

    yield TurnStartedEvent(type="turn_started")

    try:
        aiter = executor.stream_items(turn=input)
        try:
            current: RuntimeExecutorItem | None = await anext(aiter)
        except StopAsyncIteration:
            current = None

        while current is not None:
            try:
                nxt: RuntimeExecutorItem | None = await anext(aiter)
            except StopAsyncIteration:
                nxt = None

            if isinstance(current, EventItem):
                yield current.event
            else:
                is_final = True
                if nxt is not None and isinstance(nxt, TextItem):
                    is_final = False

                yield TextChunkEvent(
                    type="text_chunk",
                    content=current.content,
                    chunk_index=chunks_emitted,
                    final=is_final,
                )
                chunks_emitted += 1

            current = nxt

        duration_ms = int((monotonic() - start) * 1000)
        yield TurnCompletedEvent(
            type="turn_completed",
            duration_ms=duration_ms,
            chunks_emitted=chunks_emitted,
        )

    except Exception:
        yield TurnFailedEvent(
            type="turn_failed",
            error_code="internal_error",
            message="runtime turn failed",
            retryable=True,
        )
