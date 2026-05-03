from typing import Protocol
from collections.abc import AsyncIterator
from apps.contracts.src.schemas import RuntimeStreamEvent

from .types import (
    RunTurnInput,
    InjectEmailInput,
    ReadRuntimeFileInput,
    ReadRuntimeFileOutput,
)


class RuntimeClientPort(Protocol):
    def run_turn_stream(
        self, input: RunTurnInput
    ) -> AsyncIterator[RuntimeStreamEvent]: ...

    async def inject_email(self, input: InjectEmailInput) -> str: ...

    async def read_runtime_file(
        self, input: ReadRuntimeFileInput
    ) -> ReadRuntimeFileOutput: ...


class RuntimeClientFactoryPort(Protocol):
    def create(self, *, base_url: str) -> RuntimeClientPort: ...
