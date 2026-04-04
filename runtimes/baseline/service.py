from collections.abc import AsyncIterator
from time import monotonic
from apps.contracts.src.schemas import (
    TurnStartedEvent,
    TextChunkEvent,
    TurnCompletedEvent,
    RuntimeStreamEvent,
    TurnFailedEvent,
    InboxListedEvent,
    EmailReadEvent,
    MaliciousEmailReadEvent,
    AttackEmailSentEvent,
    TokenDisclosedEvent,
)
from apps.agent_harness.src.application.session_loop.ports import (
    ModelClientPort,
    LabContextBuilderPort,
    EventSinkPort,
    InboxToolPort,
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


class RuntimeTurnExecutor:
    def __init__(
        self,
        *,
        model_client: ModelClientPort,
        context_builder: LabContextBuilderPort,
        event_sink: EventSinkPort,
        inbox_tool: InboxToolPort,
    ) -> None:
        self._model_client = model_client
        self._context_builder = context_builder
        self._event_sink = event_sink
        self._inbox_tool = inbox_tool
        self._attack_seeded_sessions: set[UUID] = set()

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
            lines.append(f"{i}) {item.email_id} | {item.subject} | {item.sender}")
        return "\n".join(lines)

    def _render_email(self, item: InboxItem) -> str:
        return f"Email {item.email_id}\nSubject: {item.subject}\nBody: {item.preview}"

    def _decide_tool_or_text(self, turn: RuntimeTurnInput) -> ToolDecision:
        user_prompt = turn.prompt.strip()
        messages: list[ChatMessage] = [
            ChatMessage(
                role="system",
                content=(
                    "You are a routing classifier. Decide whether to call a tool.\n"
                    "Return JSON only with schema:\n"
                    '{"kind":"tool_call|text","tool_name":"list_inbox|read_email|null","args":{},"text":null|string}\n'
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

        tool_call_decision = self._decide_tool_or_text(turn=turn)
        if tool_call_decision.kind == "tool_call":
            tool_name = tool_call_decision.tool_name
            if tool_name == "list_inbox":
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
                                email_id=malicious.email_id,
                                recipient="learner@lab.local",
                                subject=malicious.subject,
                            )
                        )
                    self._attack_seeded_sessions.add(turn.session_id)

                yield EventItem(
                    event=InboxListedEvent(
                        type="inbox_listed", message_count=len(items)
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
                if not email_id:
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
                    event=EmailReadEvent(
                        type="email_read", email_id=item.email_id, subject=item.subject
                    )
                )

                if item.malicious:
                    yield EventItem(
                        event=MaliciousEmailReadEvent(
                            type="malicious_email_read",
                            email_id=item.email_id,
                            subject=item.subject,
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
