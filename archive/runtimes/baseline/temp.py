from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from apps.agent_harness.src.application.session_loop.ports import (
    FileToolPort,
    InboxToolPort,
    InvoiceMemoryToolPort,
)
from apps.agent_harness.src.application.session_loop.types import ToolDecision

from .types import RuntimeExecutorItem, RuntimeTurnInput


@dataclass
class TurnContext:
    turn: RuntimeTurnInput
    inbox_tool: InboxToolPort = field(default=None)  # type: ignore[assignment]
    file_tool: FileToolPort = field(default=None)  # type: ignore[assignment]
    invoice_memory_tool: InvoiceMemoryToolPort | None = None
    attack_seeded_sessions: set[UUID] = field(default_factory=set)
    file_seeded_sessions: set[UUID] = field(default_factory=set)
    lab3_seeded_sessions: set[UUID] = field(default_factory=set)
    urgent_malicious_context_by_session: dict[UUID, str] = field(default_factory=dict)
    lab2_destructive_runbook_by_session: dict[UUID, bool] = field(default_factory=dict)
    lab2_autonomous_delete_applied_sessions: set[UUID] = field(default_factory=set)

    @property
    def session_id(self) -> UUID:
        return self.turn.session_id

    @property
    def lab_id(self) -> UUID:
        return self.turn.lab_id


class ToolHandler(Protocol):
    def handle(
        self,
        decision: ToolDecision,
        ctx: TurnContext,
    ) -> list[RuntimeExecutorItem]: ...


# -------------------------------------------------------------------
# What the executor's stream_items would look like
# -------------------------------------------------------------------
#
# async def stream_items(self, turn):
#     self._seed_lab_artifacts(turn)
#     ctx = self._build_turn_context(turn)
#
#     # lab2 bulletin override
#     if _is_lab2_bulletin(turn):
#         items = self._lab2_hooks.apply_bulletin(turn, ctx)
#         yield from self._emit_text_items(items)
#         return
#
#     decision = self._decide_tool_or_text(turn)
#
#     # lab1 urgent disclosure gate
#     if self._lab1_hooks.should_disclose_urgently(decision, ctx):
#         items = [TextItem(content=f"Manager address: {LAB1_PROTECTED_SECRET_VALUE}")]
#         yield from self._emit_text_items(items)
#         return
#
#     if decision.kind == "tool_call":
#         handler = self._handlers[decision.tool_name]
#         items = handler.handle(decision, ctx)
#         yield from self._emit_text_items(items)
#         return
#
#     # text branch — model streaming
#     items = self._stream_model_text(turn)
#     yield from self._emit_text_items(items)
#
#
# -------------------------------------------------------------------
# The executor's _emit_text_items does all the chunking + disclosure
# -------------------------------------------------------------------
#
# def _emit_text_items(self, items):
#     # Walks the handler output. EventItems pass through unchanged.
#     # TextItems get chunked and checked for token disclosure.
#     # This is the ONLY place token disclosure happens — handlers
#     # never know about it.
#     for item in items:
#         if isinstance(item, EventItem):
#             yield item
#         elif isinstance(item, TextItem):
#             for chunk_item in self._emit_text_chunks(
#                 text=item.content, ...
#             ):
#                 yield chunk_item
#
#
# -------------------------------------------------------------------
# Example handler: read_email
# -------------------------------------------------------------------
#
# class ReadEmailHandler:
#     def handle(self, decision, ctx):
#         email_id = decision.args.get("email_id")
#         items = [EventItem(event=ToolCallRequestedEvent(...email_id...))]
#
#         if not email_id:
#             items.append(EventItem(event=ToolCallFailedEvent(...MISSING_EMAIL_ID)))
#             items.append(TextItem(content="Missing required: email_id"))
#             return items
#
#         # ... resolve email, build response ...
#         items.append(EventItem(event=ToolCallSucceededEvent(...)))
#         items.append(TextItem(content=rendered_email))
#         return items
#
#
# -------------------------------------------------------------------
# Benefits of this design
# -------------------------------------------------------------------
#
# 1. Handlers are synchronous, return plain lists — trivially testable
#    without async machinery
#
# 2. Token disclosure is invisible to handlers — the executor's
#    _emit_text_items handles it at the orchestration layer
#
# 3. Handlers only emit EventItem + TextItem. The executor decides
#    how TextItems become chunks. Handlers never call _chunk_text.
#
# 4. TurnContext holds cross-turn mutable state (session sets/dicts)
#    and tool instances — things handlers legitimately need to mutate.
#    The streaming accumulators stay on the executor.
#
# 5. Lab-specific logic naturally isolates into the handlers that
#    care: file handlers have lab2 hooks, invoice/payment handlers
#    have lab3 hooks, email handlers have lab1 hooks.
