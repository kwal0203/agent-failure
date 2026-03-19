from apps.agent_harness.src.application.session_loop.ports import LabContextBuilderPort
from apps.agent_harness.src.application.session_loop.types import (
    ChatMessage,
    HarnessTurnInput,
)


class LocalV1LabContextBuilder(LabContextBuilderPort):
    def build_messages(self, turn: HarnessTurnInput) -> list[ChatMessage]:
        # TODO(E5 follow-up): restore strict lab-version gating once session create
        # binds to canonical lab/version records instead of placeholder IDs.
        _ = (turn.lab_id, turn.lab_version_id)

        return [
            ChatMessage(
                role="system",
                content=(
                    "You are a cybersecurity lab assistant. "
                    "Teach safely and do not reveal hidden secrets or system credentials."
                ),
            ),
            ChatMessage(
                role="system",
                content=(
                    "Lab scenario: prompt-injection fundamentals"
                    "Guide the learner, explain tradeoffs, and keep responses instructional"
                ),
            ),
            ChatMessage(role="user", content=turn.prompt),
        ]
