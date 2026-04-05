from typing import Protocol
from collections.abc import AsyncIterator

from .types import RunTurnInput, RunTurnOutput
from apps.contracts.src.schemas import RuntimeStreamEvent


class RuntimeClientPort(Protocol):
    async def run_turn(self, input: RunTurnInput) -> RunTurnOutput: ...

    def run_turn_stream(
        self, input: RunTurnInput
    ) -> AsyncIterator[RuntimeStreamEvent]: ...


class RuntimeClientFactoryPort(Protocol):
    def create(self, *, base_url: str) -> RuntimeClientPort: ...
