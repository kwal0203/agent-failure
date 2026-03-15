from apps.agent_harness.src.application.session_loop.ports import EventSinkPort
from apps.agent_harness.src.application.session_loop.types import (
    HarnessChunk,
    HarnessFailure,
)


class LocalV1EventSink(EventSinkPort):
    def on_chunk(self, chunk: HarnessChunk) -> None:
        return None

    def on_failure(self, failure: HarnessFailure) -> None:
        return None
