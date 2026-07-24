from datetime import UTC, datetime
from uuid import uuid4

import pytest

from apps.contracts.src.types import (
    TRACE_EVENT_ATTACK_EMAIL_SENT,
    TRACE_EVENT_MALICIOUS_EMAIL_READ,
    TRACE_EVENT_TOKEN_DISCLOSED,
    TRACE_EVENT_TOOL_CALL_FAILED,
    TRACE_EVENT_TOOL_CALL_REQUESTED,
    TRACE_EVENT_TOOL_CALL_SUCCEEDED,
)
from apps.evaluator.src.application.rules.labs.code_execution_v1 import (
    CODE_EXECUTION_V1_BUNDLE,
)
from apps.evaluator.src.application.rules.labs.memory_poisoning_v1 import (
    MEMORY_POISONING_V1_BUNDLE,
)
from apps.evaluator.src.application.rules.labs.prompt_injection_v1 import (
    PROMPT_INJECTION_V1_BUNDLE,
)
from apps.evaluator.src.application.rules.labs.tool_misuse_v1 import (
    TOOL_MISUSE_V1_BUNDLE,
)
from apps.evaluator.src.application.rules.solution_states import (
    CodeExecutionSolutionState,
    MemoryPoisoningSolutionState,
    PromptInjectionSolutionState,
    ToolMisuseSolutionState,
)
from apps.evaluator.src.application.rules.trace_index import TraceIndex
from apps.evaluator.src.application.types import EvaluatorTraceEvent


def _event(
    *,
    event_index: int,
    family: str,
    event_type: str,
    payload: dict[str, object] | None = None,
) -> EvaluatorTraceEvent:
    return EvaluatorTraceEvent(
        event_id=uuid4(),
        session_id=uuid4(),
        family=family,
        event_type=event_type,
        occurred_at=datetime.now(UTC),
        source="test",
        event_index=event_index,
        payload=payload or {},
        trace_version=1,
        correlation_id=None,
        request_id=None,
        actor_user_id=None,
        lab_id=uuid4(),
        lab_version_id=uuid4(),
    )


@pytest.fixture
def trace() -> TraceIndex:
    return TraceIndex.build(
        (
            _event(
                event_index=1,
                family="learner",
                event_type=TRACE_EVENT_ATTACK_EMAIL_SENT,
                payload={"malicious_marker": True},
            ),
            _event(
                event_index=2,
                family="tool",
                event_type=TRACE_EVENT_TOOL_CALL_REQUESTED,
                payload={"tool_name": "read_email"},
            ),
            _event(
                event_index=3,
                family="runtime",
                event_type=TRACE_EVENT_MALICIOUS_EMAIL_READ,
                payload={"malicious_marker": True},
            ),
            _event(
                event_index=4,
                family="runtime",
                event_type=TRACE_EVENT_TOKEN_DISCLOSED,
            ),
            _event(
                event_index=5,
                family="tool",
                event_type=TRACE_EVENT_TOOL_CALL_SUCCEEDED,
                payload={"tool_name": " Bash ", "operation": " RUN "},
            ),
            _event(
                event_index=6,
                family="tool",
                event_type=TRACE_EVENT_TOOL_CALL_FAILED,
                payload={
                    "tool_name": "delete_file",
                    "target_resource": "/var/lib/prod/customer_db.sqlite",
                    "error_code": "DENIED",
                },
            ),
            _event(
                event_index=7,
                family="tool",
                event_type=TRACE_EVENT_TOOL_CALL_SUCCEEDED,
                payload={"tool_name": "write_memory", "operation": "write"},
            ),
            _event(
                event_index=8,
                family="tool",
                event_type=TRACE_EVENT_TOOL_CALL_SUCCEEDED,
                payload={"tool_name": "retrieve_memory", "operation": "retrieve"},
            ),
            _event(
                event_index=9,
                family="tool",
                event_type=TRACE_EVENT_TOOL_CALL_SUCCEEDED,
                payload={"tool_name": "pay_invoice", "operation": "pay"},
            ),
        )
    )


def test_trace_index_preserves_order_and_indexes_common_dimensions(
    trace: TraceIndex,
) -> None:
    assert tuple(event.event_index for event in trace.events) == tuple(range(1, 10))
    assert tuple(
        event.event_index for event in trace.of_type(TRACE_EVENT_TOOL_CALL_SUCCEEDED)
    ) == (5, 7, 8, 9)
    assert tuple(event.event_index for event in trace.of_family("runtime")) == (3, 4)
    assert tuple(
        event.event_index
        for event in trace.of_family_and_type(
            family="tool", event_type=TRACE_EVENT_TOOL_CALL_FAILED
        )
    ) == (6,)
    assert trace.of_type("UNKNOWN_EVENT") == ()


def test_trace_index_supports_temporal_slices(trace: TraceIndex) -> None:
    assert tuple(event.event_index for event in trace.before(4)) == (1, 2, 3)
    assert tuple(event.event_index for event in trace.before(4, inclusive=True)) == (
        1,
        2,
        3,
        4,
    )
    assert tuple(event.event_index for event in trace.after(7)) == (8, 9)
    assert tuple(event.event_index for event in trace.after(7, inclusive=True)) == (
        7,
        8,
        9,
    )


def test_prompt_injection_bundle_builds_typed_solution_state(
    trace: TraceIndex,
) -> None:
    state = PROMPT_INJECTION_V1_BUNDLE.build_solution_state(trace)

    assert isinstance(state, PromptInjectionSolutionState)
    assert tuple(event.event_index for event in state.malicious_attack_emails) == (1,)
    assert tuple(event.event_index for event in state.inbox_interactions) == (2, 3)
    assert tuple(event.event_index for event in state.malicious_email_reads) == (3,)
    assert tuple(event.event_index for event in state.token_disclosures) == (4,)


def test_tool_misuse_bundle_builds_typed_solution_state(trace: TraceIndex) -> None:
    state = TOOL_MISUSE_V1_BUNDLE.build_solution_state(trace)

    assert isinstance(state, ToolMisuseSolutionState)
    assert tuple(call.event.event_index for call in state.requested_tool_calls) == (2,)
    assert tuple(call.event.event_index for call in state.successful_tool_calls) == (
        5,
        7,
        8,
        9,
    )
    assert tuple(call.event.event_index for call in state.file_deletes) == (6,)
    assert state.file_deletes[0].error_code == "DENIED"


def test_code_execution_bundle_builds_typed_solution_state(trace: TraceIndex) -> None:
    state = CODE_EXECUTION_V1_BUNDLE.build_solution_state(trace)

    assert isinstance(state, CodeExecutionSolutionState)
    assert tuple(call.event.event_index for call in state.execution_tool_calls) == (5,)
    assert state.execution_tool_calls[0].tool_name == "bash"
    assert state.execution_tool_calls[0].operation == "run"


def test_memory_poisoning_bundle_builds_typed_solution_state(
    trace: TraceIndex,
) -> None:
    state = MEMORY_POISONING_V1_BUNDLE.build_solution_state(trace)

    assert isinstance(state, MemoryPoisoningSolutionState)
    assert tuple(call.event.event_index for call in state.memory_writes) == (7,)
    assert tuple(call.event.event_index for call in state.memory_retrievals) == (8,)
    assert tuple(call.event.event_index for call in state.invoice_payment_calls) == (9,)
