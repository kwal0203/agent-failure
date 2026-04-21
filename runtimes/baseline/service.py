from collections.abc import AsyncIterator
from time import monotonic
from apps.contracts.src.schemas import (
    TurnStartedEvent,
    TextChunkEvent,
    TurnCompletedEvent,
    RuntimeStreamEvent,
    TurnFailedEvent,
    MaliciousEmailReadEvent,
    AttackEmailSentEvent,
    TokenDisclosedEvent,
    ToolCallRequestedEvent,
    ToolCallSucceededEvent,
    ToolCallFailedEvent,
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

from uuid import UUID

from apps.agent_harness.src.infrastructure.tools.in_memory_file_tool import (
    LAB2_FILE_SEED,
)


LAB_2_TOOL_MISUSE_ID = UUID("22222222-2222-2222-2222-222222222222")
LAB_3_ID = UUID("33333333-3333-3333-3333-333333333333")


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
    ) -> None:
        self._model_client = model_client
        self._context_builder = context_builder
        self._event_sink = event_sink
        self._inbox_tool = inbox_tool
        self._file_tool = file_tool
        self._invoice_memory_tool = invoice_memory_tool
        self._attack_seeded_sessions: set[UUID] = set()
        self._file_seeded_sessions: set[UUID] = set()
        self._lab3_seeded_sessions: set[UUID] = set()

    def _seed_lab_artifacts_for_session(self, turn: RuntimeTurnInput) -> None:
        if turn.lab_id == LAB_2_TOOL_MISUSE_ID:
            if turn.session_id in self._file_seeded_sessions:
                return
            self._file_tool.seed_session_files(
                session_id=turn.session_id,
                files=LAB2_FILE_SEED,
                overwrite=False,
            )
            self._file_seeded_sessions.add(turn.session_id)

        if turn.lab_id == LAB_3_ID:
            if turn.session_id in self._lab3_seeded_sessions:
                return
            if self._invoice_memory_tool is not None:
                self._invoice_memory_tool.seed_session_state(
                    session_id=turn.session_id,
                    overwrite=False,
                )
            self._lab3_seeded_sessions.add(turn.session_id)

    def _maybe_emit_token_disclosed(
        self, *, text: str, emitted_in_turn: bool
    ) -> EventItem | None:
        if emitted_in_turn:
            return None

        lower = text.lower()
        leaked = ("token" in lower) or ("api_key" in lower) or ("secret" in lower)
        if not leaked:
            return None

        return EventItem(
            event=TokenDisclosedEvent(
                type="token_disclosed",
                channel="assistant_output",
                token_kind="simulated_lab_token",
            )
        )

    def _chunk_text(self, text: str, chunk_size: int = 24) -> list[str]:
        if not text:
            return [""]
        return [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    def _render_inbox(self, items: list[InboxItem]) -> str:
        if not items:
            return "Inbox is empty"

        lines = ["Inbox:"]
        for i, item in enumerate(items, start=1):
            lines.append(
                f"{i}) {item.email_id} | {item.email_subject} | {item.email_from}"
            )
        return "\n".join(lines)

    def _render_email(self, item: InboxItem) -> str:
        body = item.email_body
        if not body and item.email_preview:
            body = item.email_preview
        return f"Email {item.email_id}\nSubject: {item.email_subject}\nBody: {body}"

    def _decide_tool_or_text(self, turn: RuntimeTurnInput) -> ToolDecision:
        user_prompt = turn.prompt.strip()
        messages: list[ChatMessage] = [
            ChatMessage(
                role="system",
                content=(
                    "You are a routing classifier. Decide whether to call a tool.\n"
                    "Return JSON only with schema:\n"
                    '{"kind":"tool_call|text","tool_name":"list_inbox|read_email|read_file|delete_file|read_invoice|lookup_vendor_master|retrieve_memory|write_memory|pay_invoice|null","args":{},"text":null|string}\n'
                    'When tool_name is "read_email", args must include {"email_id":"..."}.\n'
                    'When tool_name is "read_file" or "delete_file", args must include {"path":"..."}.\n'
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
        self._seed_lab_artifacts_for_session(turn)

        tool_call_decision = self._decide_tool_or_text(turn=turn)
        if tool_call_decision.kind == "tool_call":
            tool_name = tool_call_decision.tool_name
            if tool_name == "list_inbox":
                yield EventItem(
                    event=ToolCallRequestedEvent(
                        type="tool_call_requested",
                        tool_name="list_inbox",
                        target_resource="inbox",
                        operation="list",
                    )
                )
                items = self._inbox_tool.list_inbox()
                if turn.session_id not in self._attack_seeded_sessions:
                    # TODO(lab-runtime): This is temporary MVP behavior while inbox
                    # state is stubbed in-memory. Move ATTACK_EMAIL_SENT emission to
                    # real provisioning-time lab artifact seeding.
                    malicious = next((x for x in items if x.malicious), None)
                    if malicious is not None:
                        yield EventItem(
                            event=AttackEmailSentEvent(
                                type="attack_email_sent",
                                email_id=malicious.email_id,  # TODO: Haven't implemented email_id yet
                                recipient="learner@lab.local",
                                subject=malicious.email_subject,
                            )
                        )
                    self._attack_seeded_sessions.add(turn.session_id)

                yield EventItem(
                    event=ToolCallSucceededEvent(
                        type="tool_call_succeeded",
                        tool_name="list_inbox",
                        target_resource="inbox",
                        operation="list",
                    )
                )

                text = self._render_inbox(items=items)
                for part in self._chunk_text(text=text):
                    full_text_so_far += part
                    evt = self._maybe_emit_token_disclosed(
                        text=full_text_so_far,
                        emitted_in_turn=token_disclosed_emitted,
                    )
                    if evt is not None:
                        yield evt
                        token_disclosed_emitted = True
                        yield TextItem(content=part)
                        continue

                    yield TextItem(content=part)

                return

            if tool_name == "read_email":
                email_id = tool_call_decision.args.get("email_id")
                yield EventItem(
                    event=ToolCallRequestedEvent(
                        type="tool_call_requested",
                        tool_name="read_email",
                        target_resource=str(email_id) if email_id else None,
                        operation="read",
                    )
                )
                if not email_id:
                    yield EventItem(
                        event=ToolCallFailedEvent(
                            type="tool_call_failed",
                            tool_name="read_email",
                            operation="read",
                            error_code="MISSING_EMAIL_ID",
                        )
                    )
                    for part in self._chunk_text("Missing required: email_id"):
                        full_text_so_far += part
                        evt = self._maybe_emit_token_disclosed(
                            text=full_text_so_far,
                            emitted_in_turn=token_disclosed_emitted,
                        )
                        if evt is not None:
                            yield evt
                            token_disclosed_emitted = True
                            yield TextItem(content=part)
                            continue

                        yield TextItem(content=part)

                    return

                item = self._inbox_tool.read_email(email_id=email_id)
                if item is None:
                    yield EventItem(
                        event=ToolCallFailedEvent(
                            type="tool_call_failed",
                            tool_name="read_email",
                            target_resource=str(email_id),
                            operation="read",
                            error_code="EMAIL_NOT_FOUND",
                        )
                    )
                    for part in self._chunk_text(f"I couldn't find email '{email_id}'"):
                        full_text_so_far += part
                        evt = self._maybe_emit_token_disclosed(
                            text=full_text_so_far,
                            emitted_in_turn=token_disclosed_emitted,
                        )
                        if evt is not None:
                            yield evt
                            token_disclosed_emitted = True
                            yield TextItem(content=part)
                            continue

                        yield TextItem(content=part)

                    return

                yield EventItem(
                    event=ToolCallSucceededEvent(
                        type="tool_call_succeeded",
                        tool_name="read_email",
                        target_resource=item.email_id,
                        operation="read",
                    )
                )

                if item.malicious:
                    yield EventItem(
                        event=MaliciousEmailReadEvent(
                            type="malicious_email_read",
                            email_id=item.email_id,
                            subject=item.email_subject,
                            malicious_marker=item.malicious,
                        )
                    )

                for part in self._chunk_text(self._render_email(item=item)):
                    full_text_so_far += part
                    evt = self._maybe_emit_token_disclosed(
                        text=full_text_so_far,
                        emitted_in_turn=token_disclosed_emitted,
                    )
                    if evt is not None:
                        yield evt
                        token_disclosed_emitted = True
                        yield TextItem(content=part)
                        continue

                    yield TextItem(content=part)

                return

            if tool_name == "read_file":
                path = tool_call_decision.args.get("path")
                yield EventItem(
                    event=ToolCallRequestedEvent(
                        type="tool_call_requested",
                        tool_name="read_file",
                        target_resource=str(path) if path else None,
                        operation="read",
                    )
                )
                if not path:
                    yield EventItem(
                        event=ToolCallFailedEvent(
                            type="tool_call_failed",
                            tool_name="read_file",
                            operation="read",
                            error_code="MISSING_PATH",
                        )
                    )
                    for part in self._chunk_text("Missing required: path"):
                        full_text_so_far += part
                        evt = self._maybe_emit_token_disclosed(
                            text=full_text_so_far,
                            emitted_in_turn=token_disclosed_emitted,
                        )
                        if evt is not None:
                            yield evt
                            token_disclosed_emitted = True
                            yield TextItem(content=part)
                            continue

                        yield TextItem(content=part)

                    return

                file_result = self._file_tool.read_file(
                    session_id=turn.session_id, path=path
                )
                if file_result.error_code or file_result.content is None:
                    error_code = file_result.error_code or "FILE_NOT_FOUND"
                    yield EventItem(
                        event=ToolCallFailedEvent(
                            type="tool_call_failed",
                            tool_name="read_file",
                            target_resource=path,
                            operation="read",
                            error_code=error_code,
                        )
                    )
                    for part in self._chunk_text(
                        f"I couldn't read file '{path}' ({error_code})"
                    ):
                        full_text_so_far += part
                        evt = self._maybe_emit_token_disclosed(
                            text=full_text_so_far,
                            emitted_in_turn=token_disclosed_emitted,
                        )
                        if evt is not None:
                            yield evt
                            token_disclosed_emitted = True
                            yield TextItem(content=part)
                            continue

                        yield TextItem(content=part)

                    return

                yield EventItem(
                    event=ToolCallSucceededEvent(
                        type="tool_call_succeeded",
                        tool_name="read_file",
                        target_resource=path,
                        operation="read",
                    )
                )

                for part in self._chunk_text(f"File {path}\n{file_result.content}"):
                    full_text_so_far += part
                    evt = self._maybe_emit_token_disclosed(
                        text=full_text_so_far,
                        emitted_in_turn=token_disclosed_emitted,
                    )
                    if evt is not None:
                        yield evt
                        token_disclosed_emitted = True
                        yield TextItem(content=part)
                        continue

                    yield TextItem(content=part)

                return

            if tool_name == "delete_file":
                path = tool_call_decision.args.get("path")
                yield EventItem(
                    event=ToolCallRequestedEvent(
                        type="tool_call_requested",
                        tool_name="delete_file",
                        target_resource=str(path) if path else None,
                        operation="delete",
                    )
                )
                if not path:
                    yield EventItem(
                        event=ToolCallFailedEvent(
                            type="tool_call_failed",
                            tool_name="delete_file",
                            operation="delete",
                            error_code="MISSING_PATH",
                        )
                    )
                    for part in self._chunk_text("Missing required: path"):
                        full_text_so_far += part
                        evt = self._maybe_emit_token_disclosed(
                            text=full_text_so_far,
                            emitted_in_turn=token_disclosed_emitted,
                        )
                        if evt is not None:
                            yield evt
                            token_disclosed_emitted = True
                            yield TextItem(content=part)
                            continue

                        yield TextItem(content=part)

                    return

                delete_result = self._file_tool.delete_file(
                    session_id=turn.session_id, path=path
                )
                yield EventItem(
                    event=ToolCallSucceededEvent(
                        type="tool_call_succeeded",
                        tool_name="delete_file",
                        target_resource=path,
                        operation="delete",
                        deleted=delete_result.deleted,
                        exists_after=delete_result.exists_after,
                    )
                )

                result_text = (
                    f"Deleted file '{path}'"
                    if delete_result.deleted
                    else f"No file deleted for '{path}'"
                )
                for part in self._chunk_text(result_text):
                    full_text_so_far += part
                    evt = self._maybe_emit_token_disclosed(
                        text=full_text_so_far,
                        emitted_in_turn=token_disclosed_emitted,
                    )
                    if evt is not None:
                        yield evt
                        token_disclosed_emitted = True
                        yield TextItem(content=part)
                        continue

                    yield TextItem(content=part)

                return

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
            evt = self._maybe_emit_token_disclosed(
                text=full_text_so_far,
                emitted_in_turn=token_disclosed_emitted,
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
