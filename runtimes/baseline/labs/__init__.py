from dataclasses import dataclass
from typing import Protocol

from apps.agent_harness.src.application.session_loop.ports import (
    FileToolPort,
    InvoiceMemoryToolPort,
)
from apps.agent_harness.src.application.session_loop.types import (
    InboxItem,
    ToolDecision,
)

from ..types import EventItem, RuntimeExecutorItem, RuntimeTurnInput
from ..handlers import ToolHandler, TurnContext


@dataclass
class PreDispatchResult:
    items: list[RuntimeExecutorItem]
    full_text_so_far: str
    token_disclosed_emitted: bool


class LabHooks(Protocol):
    def seed_artifacts(
        self,
        turn: RuntimeTurnInput,
        file_tool: FileToolPort,
        invoice_memory_tool: InvoiceMemoryToolPort | None,
    ) -> None: ...

    def pre_dispatch(
        self,
        turn: RuntimeTurnInput,
        decision: ToolDecision,
        full_text_so_far: str,
        token_disclosed_emitted: bool,
    ) -> PreDispatchResult | None: ...

    def maybe_emit_token_disclosed(
        self, text: str, emitted: bool
    ) -> EventItem | None: ...

    def on_read_file_error(
        self,
        ctx: TurnContext,
        path: str,
        error_code: str,
        items: list[RuntimeExecutorItem],
    ) -> list[RuntimeExecutorItem]: ...

    def on_email_read(
        self,
        ctx: TurnContext,
        email_item: InboxItem,
        items: list[RuntimeExecutorItem],
    ) -> None: ...

    def get_handlers(self) -> dict[str, ToolHandler]: ...


class NullLabHooks:
    def seed_artifacts(
        self,
        turn: RuntimeTurnInput,
        file_tool: FileToolPort,
        invoice_memory_tool: InvoiceMemoryToolPort | None,
    ) -> None:
        pass

    def pre_dispatch(
        self,
        turn: RuntimeTurnInput,
        decision: ToolDecision,
        full_text_so_far: str,
        token_disclosed_emitted: bool,
    ) -> PreDispatchResult | None:
        return None

    def maybe_emit_token_disclosed(self, text: str, emitted: bool) -> EventItem | None:
        return None

    def on_read_file_error(
        self,
        ctx: TurnContext,
        path: str,
        error_code: str,
        items: list[RuntimeExecutorItem],
    ) -> list[RuntimeExecutorItem]:
        return []

    def on_email_read(
        self,
        ctx: TurnContext,
        email_item: InboxItem,
        items: list[RuntimeExecutorItem],
    ) -> None:
        pass

    def get_handlers(self) -> dict[str, ToolHandler]:
        return {}
