from apps.agent_harness.src.interfaces.runtime.dependencies import (
    get_context_builder,
    get_event_sink,
    get_model_client,
)
from apps.agent_harness.src.infrastructure.tools.in_memory_inbox_tool import InMemoryInboxTool

from .service import RuntimeTurnExecutor


def get_runtime_executor() -> RuntimeTurnExecutor:
    return RuntimeTurnExecutor(
        model_client=get_model_client(),
        context_builder=get_context_builder(),
        event_sink=get_event_sink(),
        inbox_tool=InMemoryInboxTool(),
    )
