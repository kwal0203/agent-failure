from apps.agent_harness.src.application.session_loop.ports import LabContextBuilderPort
from apps.agent_harness.src.application.session_loop.types import (
    ChatMessage,
    HarnessTurnInput,
)

from .prompts import SYSTEM_PROMPT_EASY, SYSTEM_PROMPT_MEDIUM, SYSTEM_PROMPT_HARD
from .types import DifficultyConfig
from apps.agent_harness.src.infrastructure.config.settings import get_lab_difficulty


_CONFIG_BY_DIFFICULTY: dict[str, DifficultyConfig] = {
    "easy": DifficultyConfig(system_prompt=SYSTEM_PROMPT_EASY),
    "medium": DifficultyConfig(system_prompt=SYSTEM_PROMPT_MEDIUM),
    "hard": DifficultyConfig(system_prompt=SYSTEM_PROMPT_HARD),
}


def _active_difficulty() -> str:
    return get_lab_difficulty()


class LabContextBuilder(LabContextBuilderPort):
    def build_messages(self, turn: HarnessTurnInput) -> list[ChatMessage]:
        # TODO(E5 follow-up): restore strict lab-version gating once session create
        # binds to canonical lab/version records instead of placeholder IDs.

        # TODO(lab-context): MVP currently rebuilds context per turn from
        # difficulty config + latest user prompt only. Add durable transcript
        # or summarized memory so each turn includes prior conversation history.

        config = _CONFIG_BY_DIFFICULTY[_active_difficulty()]
        return [
            ChatMessage(role="system", content=config.system_prompt),
            ChatMessage(role="user", content=turn.prompt),
        ]
