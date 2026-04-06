from typing import Protocol
from collections.abc import AsyncIterator
from apps.contracts.src.schemas import RuntimeStreamEvent

from .types import RunTurnInput, RunTurnOutput, InjectEmailInput


class RuntimeClientPort(Protocol):
    async def run_turn(self, input: RunTurnInput) -> RunTurnOutput: ...

    def run_turn_stream(
        self, input: RunTurnInput
    ) -> AsyncIterator[RuntimeStreamEvent]: ...

    async def inject_email(self, input: InjectEmailInput) -> None: ...


class RuntimeClientFactoryPort(Protocol):
    def create(self, *, base_url: str) -> RuntimeClientPort: ...
