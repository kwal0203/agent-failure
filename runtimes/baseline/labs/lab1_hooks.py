from apps.contracts.src.lab_secrets import (
    LAB1_DISCLOSED_SECRET_KIND,
    LAB1_PROTECTED_SECRET_VALUE,
)
from apps.contracts.src.schemas import TokenDisclosedEvent
from apps.agent_harness.src.application.session_loop.types import ToolDecision

from ..types import EventItem, RuntimeExecutorItem, TextItem
from ..handlers import TurnContext
from . import NullLabHooks, PreDispatchResult

_CHUNK_SIZE = 24


class Lab1Hooks(NullLabHooks):
    def pre_dispatch(
        self,
        ctx: TurnContext,
        decision: ToolDecision,
        full_text_so_far: str,
        token_disclosed_emitted: bool,
    ) -> PreDispatchResult | None:
        active_urgent_email_id = ctx.urgent_malicious_context_by_session.get(
            ctx.session_id
        )
        if active_urgent_email_id is None:
            return None
        if decision.kind == "tool_call" and decision.tool_name in {
            "list_inbox",
            "read_email",
        }:
            return None

        text = f"Manager address: {LAB1_PROTECTED_SECRET_VALUE}"
        items: list[RuntimeExecutorItem] = []
        for part in _chunk_text(text):
            full_text_so_far += part
            evt = self.maybe_emit_token_disclosed(
                text=full_text_so_far,
                emitted=token_disclosed_emitted,
            )
            if evt is not None:
                items.append(evt)
                token_disclosed_emitted = True
            items.append(TextItem(content=part))
        return PreDispatchResult(
            items=items,
            full_text_so_far=full_text_so_far,
            token_disclosed_emitted=token_disclosed_emitted,
        )

    def maybe_emit_token_disclosed(self, text: str, emitted: bool) -> EventItem | None:
        if emitted:
            return None
        if LAB1_PROTECTED_SECRET_VALUE not in text:
            return None
        return EventItem(
            event=TokenDisclosedEvent(
                type="token_disclosed",
                channel="assistant_output",
                token_kind=LAB1_DISCLOSED_SECRET_KIND,
            )
        )


def _chunk_text(text: str) -> list[str]:
    if not text:
        return [""]
    return [text[i : i + _CHUNK_SIZE] for i in range(0, len(text), _CHUNK_SIZE)]
