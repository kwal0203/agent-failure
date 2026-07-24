from apps.agent_harness.src.application.session_loop.ports import LabContextBuilderPort
from apps.agent_harness.src.application.session_loop.types import (
    ChatMessage,
    HarnessTurnInput,
)

from .prompts import SYSTEM_PROMPT


class LabContextBuilder(LabContextBuilderPort):
    def build_messages(self, turn: HarnessTurnInput) -> list[ChatMessage]:
        # TODO(E5 follow-up): restore strict lab-version gating once session create
        # binds to canonical lab/version records instead of placeholder IDs.

        # TODO(lab-context): MVP currently rebuilds context per turn from the
        # lab prompt + latest user prompt only. Add durable transcript
        # or summarized memory so each turn includes prior conversation history.

        return [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content=turn.prompt),
        ]
