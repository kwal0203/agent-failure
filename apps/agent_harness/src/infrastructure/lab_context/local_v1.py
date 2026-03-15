from apps.agent_harness.src.application.session_loop.ports import LabContextBuilder
from apps.agent_harness.src.application.session_loop.types import (
    ChatMessage,
    HarnessTurnInput,
)

from uuid import UUID


class LocalV1LabContextBuilder(LabContextBuilder):
    SUPPORTED_LAB_ID: UUID = UUID("11111111-1111-1111-1111-111111111111")
    SUPPORTED_LAB_VERSION_ID: UUID = UUID("22222222-2222-2222-2222-222222222222")

    def build_messages(self, turn: HarnessTurnInput) -> list[ChatMessage]:
        if (
            turn.lab_id != self.SUPPORTED_LAB_ID
            or turn.lab_version_id != self.SUPPORTED_LAB_VERSION_ID
        ):
            raise ValueError("unsupported_lab_path")

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
