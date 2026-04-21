from apps.agent_harness.src.interfaces.runtime.dependencies import (
    get_context_builder,
    get_event_sink,
    get_model_client,
)
from apps.agent_harness.src.infrastructure.tools.in_memory_inbox_tool import (
    InMemoryInboxTool,
)
from apps.agent_harness.src.infrastructure.tools.in_memory_file_tool import (
    InMemoryFileTool,
)
from apps.agent_harness.src.infrastructure.tools.in_memory_invoice_tool import (
    InMemoryInvoiceTool,
)

from .service import RuntimeTurnExecutor


# TODO(lab1-persistence): MVP shortcut. Process-level singleton state keeps
# injected inbox artifacts visible across requests in one runtime pod, but this
# is not durable and not safe for multi-process/multi-replica deployments.
# Replace with session-scoped durable inbox storage (repository/DB) as source
# of truth, and keep in-memory state as an optional cache only.
_INBOX_TOOL = InMemoryInboxTool()
_FILE_TOOL = InMemoryFileTool()
_INVOICE_MEMORY_TOOL = InMemoryInvoiceTool()
_EXECUTOR = RuntimeTurnExecutor(
    model_client=get_model_client(),
    context_builder=get_context_builder(),
    event_sink=get_event_sink(),
    inbox_tool=_INBOX_TOOL,
    file_tool=_FILE_TOOL,
    invoice_memory_tool=_INVOICE_MEMORY_TOOL,
)


def get_runtime_executor() -> RuntimeTurnExecutor:
    return _EXECUTOR
