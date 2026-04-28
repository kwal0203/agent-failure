# Agent Runtime Event Emission — Implementation Plan

## Goal

Make the agent runtime (`runtimes/agent/`) emit the same structured ndjson events as the baseline runtime (`runtimes/baseline/`), so the control plane can persist trace events and the evaluator can score sessions.

## Current State

The agent runtime only emits 4 event types in its ndjson stream:
- `turn_started`
- `text_chunk`
- `turn_completed`
- `turn_failed`

The baseline runtime emits all of the above **plus**:
- `tool_call_requested` — before every tool execution
- `tool_call_succeeded` — after successful tool execution (includes tool-specific fields like `target_resource`, `operation`, `deleted`, `bytes_written`, etc.)
- `tool_call_failed` — after failed tool execution (includes `error_code`, `qualifying_log`, `log_case`)
- `attack_email_sent` — when a malicious email is detected in inbox (lab 1)
- `malicious_email_read` — when a malicious email is read (lab 1)
- `token_disclosed` — when a protected secret appears in output text (lab 1)

## Architecture Overview

### How the baseline does it

```
handlers.py  →  returns list[RuntimeExecutorItem]
                   ├── EventItem(event=ToolCallRequestedEvent(...))
                   ├── EventItem(event=ToolCallSucceededEvent(...))
                   └── TextItem(content="...")

service.py   →  stream_items() yields RuntimeExecutorItem
             →  stream_turn_events() converts to RuntimeStreamEvent
                   ├── EventItem → yield event directly
                   └── TextItem  → wrap in TextChunkEvent

main.py      →  event_stream() serializes each RuntimeStreamEvent as ndjson line
```

Key types (from `runtimes/baseline/types.py`):
```python
@dataclass(frozen=True)
class TextItem:
    content: str

@dataclass(frozen=True)
class EventItem:
    event: RuntimeStreamEvent

RuntimeExecutorItem = TextItem | EventItem
```

`RuntimeStreamEvent` is a Pydantic discriminated union from `apps/contracts/src/schemas.py` covering all 11 event types.

### How the agent should do it

The agent's `run_agent_turn()` currently yields `str` (raw text). It needs to yield a union type that includes both text and structured events. The cleanest approach is to reuse the same `TextItem | EventItem` pattern.

```
agent.py     →  run_agent_turn() yields AgentTurnItem (TextItem | EventItem)
                   ├── TextItem for agent text output
                   ├── EventItem(ToolCallRequestedEvent) before dispatch
                   ├── EventItem(ToolCallSucceededEvent) on success
                   └── EventItem(ToolCallFailedEvent) on failure

main.py      →  event_stream() handles both:
                   ├── EventItem → serialize event as ndjson line
                   └── TextItem  → chunk into TextChunkEvent lines
```

---

## Tier 1: Tool Call Events (no lab hooks)

### Step 1: Define `AgentTurnItem` type

**File:** `runtimes/agent/types.py`

Add:
```python
from apps.contracts.src.schemas import RuntimeStreamEvent

@dataclass(frozen=True)
class TextItem:
    content: str

@dataclass(frozen=True)
class EventItem:
    event: RuntimeStreamEvent

AgentTurnItem = TextItem | EventItem
```

This mirrors the baseline's `RuntimeExecutorItem = TextItem | EventItem` from `runtimes/baseline/types.py`.

### Step 2: Update `run_agent_turn()` yield type

**File:** `runtimes/agent/agent.py`

Change the return type from `AsyncIterator[str]` to `AsyncIterator[AgentTurnItem]`.

Instead of:
```python
yield response.content
```

Do:
```python
yield TextItem(content=response.content)
```

### Step 3: Emit tool call events in the dispatch loop

**File:** `runtimes/agent/agent.py`

In the tool dispatch loop (lines 119-128), wrap each dispatch with events:

```python
for tc in response.tool_calls:
    yield EventItem(event=ToolCallRequestedEvent(
        type="tool_call_requested",
        tool_name=tc.tool_name,
        target_resource=_extract_target(tc),
        operation=_extract_operation(tc),
    ))

    result = dispatch(tc, ctx)

    if result.success:
        yield EventItem(event=ToolCallSucceededEvent(
            type="tool_call_succeeded",
            tool_name=tc.tool_name,
            target_resource=_extract_target(tc),
            operation=_extract_operation(tc),
        ))
    else:
        yield EventItem(event=ToolCallFailedEvent(
            type="tool_call_failed",
            tool_name=tc.tool_name,
            target_resource=_extract_target(tc),
            operation=_extract_operation(tc),
            error_code="TOOL_ERROR" if not result.success else None,
        ))

    messages.append(
        ChatMessage(
            role="tool",
            content=result.output,
            tool_call_id=tc.call_id,
            tool_name=tc.tool_name,
        )
    )
```

Helper functions to extract target/operation from tool name and arguments:
```python
def _extract_target(tc: ToolCall) -> str | None:
    if tc.tool_name == "read_email":
        return str(tc.arguments.get("email_id", ""))
    if tc.tool_name in ("read_file", "write_file", "delete_file"):
        return str(tc.arguments.get("path", ""))
    if tc.tool_name == "read_invoice":
        return str(tc.arguments.get("invoice_id", ""))
    if tc.tool_name == "lookup_vendor_master":
        return str(tc.arguments.get("vendor_name", ""))
    if tc.tool_name in ("retrieve_memory", "write_memory"):
        return str(tc.arguments.get("query", "")) or str(tc.arguments.get("memory_type", ""))
    return None

def _extract_operation(tc: ToolCall) -> str | None:
    ops = {
        "read_email": "read", "list_inbox": "list",
        "read_file": "read", "write_file": "write", "delete_file": "delete",
        "read_invoice": "read", "lookup_vendor_master": "lookup",
        "retrieve_memory": "retrieve", "write_memory": "write",
        "list_tools": "list",
    }
    return ops.get(tc.tool_name)
```

### Step 4: Update `main.py` event_stream to handle both types

**File:** `runtimes/agent/main.py`

The `event_stream()` function currently treats everything as text. Change it to:

```python
async def event_stream() -> AsyncIterator[str]:
    start = monotonic()
    chunks = 0
    yield TurnStartedEvent(type="turn_started").model_dump_json() + "\n"

    try:
        async for item in run_agent_turn(
            prompt=request.prompt,
            llm=_LLM,
            ctx=ctx,
            system_prompt=system_prompt,
            tools=active_tools,
        ):
            if isinstance(item, EventItem):
                yield item.event.model_dump_json() + "\n"
            else:
                # TextItem — chunk into 24-char TextChunkEvents
                text = item.content
                chunk_size = 24
                for i in range(0, len(text), chunk_size):
                    part = text[i : i + chunk_size]
                    is_final = (i + chunk_size >= len(text))
                    yield TextChunkEvent(
                        type="text_chunk",
                        content=part,
                        chunk_index=chunks,
                        final=is_final,
                    ).model_dump_json() + "\n"
                    chunks += 1

        duration_ms = int((monotonic() - start) * 1000)
        yield TurnCompletedEvent(...).model_dump_json() + "\n"
    except Exception:
        yield TurnFailedEvent(...).model_dump_json() + "\n"
```

### Step 5: Update imports

**File:** `runtimes/agent/main.py`

Add imports:
```python
from apps.contracts.src.schemas import (
    # existing...
    ToolCallRequestedEvent,
    ToolCallSucceededEvent,
    ToolCallFailedEvent,
)
from .types import TextItem, EventItem
```

**File:** `runtimes/agent/agent.py`

Add imports:
```python
from apps.contracts.src.schemas import (
    ToolCallRequestedEvent,
    ToolCallSucceededEvent,
    ToolCallFailedEvent,
)
from .types import ChatMessage, LLMResponse, TextResponse, ToolCall, ToolCallResponse, ToolDef, TextItem, EventItem
```

### Step 6: Update tests

**File:** `runtimes/agent/tests/conftest.py`

Update `run_turn()` helper to handle the new yield type:
```python
async def run_turn(
    *,
    prompt: str = "hello",
    llm: LLMClient,
    ctx: ToolCtx | None = None,
) -> str:
    parts: list[str] = []
    async for item in run_agent_turn(
        prompt=prompt,
        llm=llm,
        ctx=ctx or make_ctx(),
    ):
        if isinstance(item, TextItem):
            parts.append(item.content)
    return "".join(parts)
```

Also add a helper to collect events:
```python
async def run_turn_collect_events(
    *,
    prompt: str = "hello",
    llm: LLMClient,
    ctx: ToolCtx | None = None,
) -> tuple[str, list[EventItem]]:
    text_parts: list[str] = []
    events: list[EventItem] = []
    async for item in run_agent_turn(
        prompt=prompt,
        llm=llm,
        ctx=ctx or make_ctx(),
    ):
        if isinstance(item, TextItem):
            text_parts.append(item.content)
        else:
            events.append(item)
    return "".join(text_parts), events
```

**File:** `runtimes/agent/tests/test_agent.py`

Update existing tests (they currently assert on `result` being a string from `run_turn()`, which still works since `run_turn` will extract text).

Add new tests:
```python
@pytest.mark.asyncio
async def test_tool_call_emits_requested_and_succeeded_events():
    """Verify tool dispatch yields ToolCallRequested then ToolCallSucceeded."""
    ...

@pytest.mark.asyncio
async def test_unknown_tool_emits_failed_event():
    """Verify unknown tool yields ToolCallRequested then ToolCallFailed."""
    ...
```

### Step 7: Run all tests

```bash
.venv/bin/python -m pytest runtimes/agent/tests/ runtimes/baseline/tests/ -v
```

---

## Tier 2: Lab Hooks (reactive behavior)

This tier adds lab-specific event emission and reactive behavior. It builds on the `AgentTurnItem` yield pattern established in Tier 1.

### Step 2.1: Define `AgentLabHooks` protocol

**New file:** `runtimes/agent/hooks.py`

```python
from __future__ import annotations

from typing import Protocol

from .types import AgentTurnItem, ToolCall, ToolResult
from .tools import ToolCtx


class AgentLabHooks(Protocol):
    def on_tool_dispatch(
        self,
        call: ToolCall,
        result: ToolResult,
        ctx: ToolCtx,
    ) -> list[AgentTurnItem]:
        """Called after each tool dispatch. Return additional items to emit."""
        ...

    def on_text_output(
        self,
        text: str,
    ) -> list[AgentTurnItem]:
        """Called when the agent produces text output. Return additional items (e.g., TokenDisclosedEvent)."""
        ...

    def seed(
        self,
        ctx: ToolCtx,
    ) -> None:
        """Called once per session to seed initial state."""
        ...


class NullAgentLabHooks:
    def on_tool_dispatch(self, call: ToolCall, result: ToolResult, ctx: ToolCtx) -> list[AgentTurnItem]:
        return []

    def on_text_output(self, text: str) -> list[AgentTurnItem]:
        return []

    def seed(self, ctx: ToolCtx) -> None:
        pass
```

### Step 2.2: Wire hooks into `run_agent_turn()`

**File:** `runtimes/agent/agent.py`

Add `hooks: AgentLabHooks | None = None` parameter. Call `hooks.on_tool_dispatch()` after each dispatch and yield the results. Call `hooks.on_text_output()` when the agent produces text.

### Step 2.3: Wire hooks into lab configs

**File:** `runtimes/agent/lab_configs/_types.py`

Add optional `hooks_factory` to `LabConfig`:
```python
@dataclass(frozen=True)
class LabConfig:
    ...
    hooks_factory: Callable[[], AgentLabHooks] | None = None
```

Each lab config module defines its hooks class and attaches it.

### Step 2.4: Lab 1 — Prompt Injection hooks

**File:** `runtimes/agent/lab_configs/lab_001_prompt_injection.py`

- `on_text_output()` — scan text for `LAB1_PROTECTED_SECRET_VALUE`, emit `TokenDisclosedEvent` if found (only once)
- `seed()` — no-op (the secret is in the system prompt)

Baseline reference: `runtimes/baseline/labs/lab1_hooks.py` — the `pre_dispatch` method forces secret disclosure by hijacking non-email tool calls. In the agent runtime, the vulnerability is more natural: the LLM itself outputs the secret because the system prompt tells it to under compliance urgency. We just need to detect when it happens.

### Step 2.5: Lab 2 — Tool Misuse hooks

**File:** `runtimes/agent/lab_configs/lab_002_tool_misuse.py`

- `seed()` — seed the ops runbook file using `SeedConfig`
- `on_tool_dispatch()` for `read_file` failures — emit `ToolCallFailedEvent` with `qualifying_log=True` and `log_case="missing_recovery_artifact"`
- Authority bulletin handling — this is triggered by `RunTurnStreamRequest.authority_bulletin_passed`. The hook should overwrite the runbook with poisoned content when this flag is set. This may need to be a separate hook method or handled in `seed()`.

Baseline reference: `runtimes/baseline/labs/lab2_hooks.py` — `pre_dispatch` handles the authority bulletin overwrite, `on_read_file_error` handles the autonomous delete.

### Step 2.6: Lab 3 — Memory Poisoning hooks

**File:** `runtimes/agent/lab_configs/lab_003_memory_poisoning.py`

- `seed()` — seed invoice memory state
- `on_tool_dispatch()` for `read_email` — detect authoritative remittance update emails and write memory
- Add `pay_invoice` tool to `TOOLS` and `dispatch` — port the `PayInvoiceHandler` logic

Baseline reference: `runtimes/baseline/labs/lab3_hooks.py` — `on_email_read` writes authoritative remittance memory, `get_handlers` provides `PayInvoiceHandler`.

### Step 2.7: Wire seeding into `main.py`

**File:** `runtimes/agent/main.py`

Track seeded sessions with a `set[UUID]`. On each turn, call `hooks.seed(ctx)` if the session hasn't been seeded yet.

---

## Key Reference Files

| Purpose | File |
|---------|------|
| Agent loop (to modify) | `runtimes/agent/agent.py` |
| Agent HTTP endpoint (to modify) | `runtimes/agent/main.py` |
| Agent types (to add TextItem/EventItem) | `runtimes/agent/types.py` |
| Agent tool dispatch (no changes needed) | `runtimes/agent/tools.py` |
| Lab config types | `runtimes/agent/lab_configs/_types.py` |
| Lab 1 config | `runtimes/agent/lab_configs/lab_001_prompt_injection.py` |
| Lab 2 config | `runtimes/agent/lab_configs/lab_002_tool_misuse.py` |
| Lab 3 config | `runtimes/agent/lab_configs/lab_003_memory_poisoning.py` |
| Test helpers (to update) | `runtimes/agent/tests/conftest.py` |
| Agent tests (to update + add) | `runtimes/agent/tests/test_agent.py` |
| Baseline types pattern (reference) | `runtimes/baseline/types.py` |
| Baseline event emission pattern (reference) | `runtimes/baseline/handlers.py` |
| Baseline streaming pattern (reference) | `runtimes/baseline/service.py:248-300` |
| Baseline lab hooks (reference) | `runtimes/baseline/labs/lab1_hooks.py`, `lab2_hooks.py`, `lab3_hooks.py` |
| Event schemas (all event types) | `apps/contracts/src/schemas.py` |
| Lab secrets | `apps/contracts/src/lab_secrets.py` |
| Control plane event persistence | `apps/control_plane/src/interfaces/http/main.py` (handle_user_prompt) |

## Implementation Order

1. Steps 1-7 (Tier 1) — structural change, tool call events
2. Step 2.1-2.2 — hooks protocol + wiring
3. Step 2.7 — seeding infrastructure
4. Step 2.4 — Lab 1 hooks (simplest)
5. Step 2.5 — Lab 2 hooks
6. Step 2.6 — Lab 3 hooks (most complex, needs `pay_invoice` tool)
