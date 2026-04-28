import os
from uuid import UUID

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
from .labs import LabHooks, NullLabHooks
from .labs.lab1_hooks import Lab1Hooks
from .labs.lab2_hooks import Lab2Hooks, LAB_2_TOOL_MISUSE_ID
from .labs.lab3_hooks import Lab3Hooks, LAB_3_ID

_LAB_1_ID = UUID("11111111-1111-1111-1111-111111111111")


def _make_hooks(file_tool: InMemoryFileTool) -> LabHooks:
    raw = os.getenv("LAB_ID", "").strip()
    if not raw:
        return NullLabHooks()
    try:
        lab_id = UUID(raw)
    except ValueError:
        return NullLabHooks()
    if lab_id == _LAB_1_ID:
        return Lab1Hooks()
    if lab_id == LAB_2_TOOL_MISUSE_ID:
        return Lab2Hooks(file_tool=file_tool)
    if lab_id == LAB_3_ID:
        return Lab3Hooks()
    return NullLabHooks()


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
    hooks=_make_hooks(_FILE_TOOL),
)


def get_runtime_executor() -> RuntimeTurnExecutor:
    return _EXECUTOR
