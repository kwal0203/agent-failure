from typing import Iterable

from apps.agent_harness.src.application.session_loop.ports import ModelClientPort
from apps.agent_harness.src.application.session_loop.types import (
    HarnessChunk,
    ModelRequest,
)


class LocalV1ModelClient(ModelClientPort):
    def __init__(self) -> None:
        super().__init__()

    def stream(self, payload: ModelRequest) -> Iterable[HarnessChunk]:
        user_prompt = next(
            (m.content for m in payload.messages if m.role == "user"),
            "",
        )
        yield HarnessChunk(content="I can help with that. ", final=False)
        yield HarnessChunk(content=f"You asked: {user_prompt}", final=True)
