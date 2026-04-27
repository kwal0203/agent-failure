from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from apps.agent_harness.src.application.session_loop.ports import (
    FileToolPort,
    InboxToolPort,
    InvoiceMemoryToolPort,
)
from apps.agent_harness.src.application.session_loop.types import (
    InboxItem,
    ToolDecision,
)
from apps.contracts.src.schemas import (
    AttackEmailSentEvent,
    ToolCallRequestedEvent,
    ToolCallSucceededEvent,
)
from apps.contracts.src.types import CANONICAL_TOOL_ARGS_REQUIRED

from .types import EventItem, RuntimeExecutorItem, RuntimeTurnInput, TextItem


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


class ListToolsHandler:
    def handle(
        self,
        decision: ToolDecision,
        ctx: TurnContext,
    ) -> list[RuntimeExecutorItem]:
        catalog = self._render_tool_catalog()
        return [
            EventItem(
                event=ToolCallRequestedEvent(
                    type="tool_call_requested",
                    tool_name="list_tools",
                    target_resource="tools",
                    operation="list",
                )
            ),
            EventItem(
                event=ToolCallSucceededEvent(
                    type="tool_call_succeeded",
                    tool_name="list_tools",
                    target_resource="tools",
                    operation="list",
                )
            ),
            TextItem(content=catalog),
        ]

    @staticmethod
    def _render_tool_catalog() -> str:
        lines = ["Available tools:"]
        for tool_name, required_args in CANONICAL_TOOL_ARGS_REQUIRED.items():
            if not required_args:
                lines.append(f"- {tool_name}()")
                continue
            args_csv = ", ".join(required_args)
            lines.append(f"- {tool_name}({args_csv})")
        return "\n".join(lines)


class ListInboxHandler:
    def handle(
        self,
        decision: ToolDecision,
        ctx: TurnContext,
    ) -> list[RuntimeExecutorItem]:
        items: list[RuntimeExecutorItem] = [
            EventItem(
                event=ToolCallRequestedEvent(
                    type="tool_call_requested",
                    tool_name="list_inbox",
                    target_resource="inbox",
                    operation="list",
                )
            ),
        ]

        inbox_items = ctx.inbox_tool.list_inbox()
        if ctx.session_id not in ctx.attack_seeded_sessions:
            malicious = next((x for x in inbox_items if x.malicious), None)
            if malicious is not None:
                items.append(
                    EventItem(
                        event=AttackEmailSentEvent(
                            type="attack_email_sent",
                            email_id=malicious.email_id,
                            recipient="learner@lab.local",
                            subject=malicious.email_subject,
                        )
                    )
                )
            ctx.attack_seeded_sessions.add(ctx.session_id)

        items.append(
            EventItem(
                event=ToolCallSucceededEvent(
                    type="tool_call_succeeded",
                    tool_name="list_inbox",
                    target_resource="inbox",
                    operation="list",
                )
            )
        )

        items.append(TextItem(content=self._render_inbox(inbox_items)))
        return items

    @staticmethod
    def _render_inbox(inbox_items: list[InboxItem]) -> str:
        if not inbox_items:
            return "Inbox is empty"

        email_id_to_alias, _ = _build_email_alias_maps(items=inbox_items)
        lines = ["Inbox:"]
        for item in inbox_items:
            body = item.email_body
            if not body and item.email_preview:
                body = item.email_preview
            display_id = email_id_to_alias.get(item.email_id, item.email_id)
            lines.append(f"ID: {display_id}")
            lines.append(f"Subject: {item.email_subject}")
            lines.append(f"Body: {body}")
            lines.append("")
        if lines[-1] == "":
            lines.pop()
        return "\n".join(lines)


def _build_email_alias_maps(
    *, items: list[InboxItem]
) -> tuple[dict[str, str], dict[str, str]]:
    email_id_to_alias: dict[str, str] = {}
    alias_to_email_id: dict[str, str] = {}
    for index, item in enumerate(items, start=1):
        alias = f"e{index}"
        email_id_to_alias[item.email_id] = alias
        alias_to_email_id[alias] = item.email_id
    return email_id_to_alias, alias_to_email_id
