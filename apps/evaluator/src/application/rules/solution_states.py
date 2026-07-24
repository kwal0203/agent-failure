from dataclasses import dataclass

from apps.contracts.src.types import (
    TRACE_EVENT_ATTACK_EMAIL_SENT,
    TRACE_EVENT_MALICIOUS_EMAIL_READ,
    TRACE_EVENT_TOKEN_DISCLOSED,
    TRACE_EVENT_TOOL_CALL_FAILED,
    TRACE_EVENT_TOOL_CALL_REQUESTED,
    TRACE_EVENT_TOOL_CALL_SUCCEEDED,
)
from apps.evaluator.src.application.types import EvaluatorTraceEvent

from .trace_index import TraceIndex


EXECUTION_TOOL_NAMES = frozenset({"python", "python3", "bash", "sh", "exec", "shell"})


@dataclass(frozen=True)
class ToolCallObservation:
    event: EvaluatorTraceEvent
    tool_name: str | None
    operation: str | None
    target_resource: str | None
    error_code: str | None


@dataclass(frozen=True)
class LabSolutionState:
    """Base type for a lab's deterministic interpretation of a trace window."""

    trace: TraceIndex


@dataclass(frozen=True)
class PromptInjectionSolutionState(LabSolutionState):
    learner_events: tuple[EvaluatorTraceEvent, ...]
    attack_emails: tuple[EvaluatorTraceEvent, ...]
    malicious_attack_emails: tuple[EvaluatorTraceEvent, ...]
    benign_attack_emails: tuple[EvaluatorTraceEvent, ...]
    inbox_interactions: tuple[EvaluatorTraceEvent, ...]
    malicious_email_reads: tuple[EvaluatorTraceEvent, ...]
    benign_email_reads: tuple[EvaluatorTraceEvent, ...]
    token_disclosures: tuple[EvaluatorTraceEvent, ...]


@dataclass(frozen=True)
class ToolMisuseSolutionState(LabSolutionState):
    learner_prompts: tuple[EvaluatorTraceEvent, ...]
    requested_tool_calls: tuple[ToolCallObservation, ...]
    successful_tool_calls: tuple[ToolCallObservation, ...]
    failed_tool_calls: tuple[ToolCallObservation, ...]
    file_reads: tuple[ToolCallObservation, ...]
    file_deletes: tuple[ToolCallObservation, ...]


@dataclass(frozen=True)
class CodeExecutionSolutionState(LabSolutionState):
    successful_tool_calls: tuple[ToolCallObservation, ...]
    execution_tool_calls: tuple[ToolCallObservation, ...]


@dataclass(frozen=True)
class MemoryPoisoningSolutionState(LabSolutionState):
    requested_tool_calls: tuple[ToolCallObservation, ...]
    successful_tool_calls: tuple[ToolCallObservation, ...]
    failed_tool_calls: tuple[ToolCallObservation, ...]
    memory_writes: tuple[ToolCallObservation, ...]
    memory_retrievals: tuple[ToolCallObservation, ...]
    invoice_payment_calls: tuple[ToolCallObservation, ...]


def _normalized_payload_string(event: EvaluatorTraceEvent, *keys: str) -> str | None:
    for key in keys:
        raw_value = event.payload.get(key)
        if isinstance(raw_value, str):
            value = raw_value.strip()
            if value:
                return value
    return None


def _tool_call_observation(event: EvaluatorTraceEvent) -> ToolCallObservation:
    tool_name = _normalized_payload_string(event, "tool_name")
    operation = _normalized_payload_string(event, "operation")
    return ToolCallObservation(
        event=event,
        tool_name=tool_name.lower() if tool_name is not None else None,
        operation=operation.lower() if operation is not None else None,
        target_resource=_normalized_payload_string(
            event, "target_resource", "path", "file_path", "resource"
        ),
        error_code=_normalized_payload_string(event, "error_code"),
    )


def _tool_calls(trace: TraceIndex, event_type: str) -> tuple[ToolCallObservation, ...]:
    return tuple(_tool_call_observation(event) for event in trace.of_type(event_type))


def build_prompt_injection_solution_state(
    trace: TraceIndex,
) -> PromptInjectionSolutionState:
    attack_emails = trace.of_family_and_type(
        family="learner", event_type=TRACE_EVENT_ATTACK_EMAIL_SENT
    )
    email_reads = trace.of_family_and_type(
        family="runtime", event_type=TRACE_EVENT_MALICIOUS_EMAIL_READ
    )

    inbox_tool_events = tuple(
        event
        for event_type in (
            TRACE_EVENT_TOOL_CALL_REQUESTED,
            TRACE_EVENT_TOOL_CALL_SUCCEEDED,
        )
        for event in trace.of_family_and_type(family="tool", event_type=event_type)
        if event.payload.get("tool_name") in {"list_inbox", "read_email"}
    )
    inbox_interactions = tuple(
        sorted((*email_reads, *inbox_tool_events), key=lambda event: event.event_index)
    )

    return PromptInjectionSolutionState(
        trace=trace,
        learner_events=trace.of_family("learner"),
        attack_emails=attack_emails,
        malicious_attack_emails=tuple(
            event
            for event in attack_emails
            if event.payload.get("malicious_marker") is True
        ),
        benign_attack_emails=tuple(
            event
            for event in attack_emails
            if event.payload.get("malicious_marker") is False
        ),
        inbox_interactions=inbox_interactions,
        malicious_email_reads=tuple(
            event
            for event in email_reads
            if event.payload.get("malicious_marker") is True
        ),
        benign_email_reads=tuple(
            event
            for event in email_reads
            if event.payload.get("malicious_marker") is False
        ),
        token_disclosures=trace.of_type(TRACE_EVENT_TOKEN_DISCLOSED),
    )


def build_tool_misuse_solution_state(trace: TraceIndex) -> ToolMisuseSolutionState:
    requested = _tool_calls(trace, TRACE_EVENT_TOOL_CALL_REQUESTED)
    succeeded = _tool_calls(trace, TRACE_EVENT_TOOL_CALL_SUCCEEDED)
    failed = _tool_calls(trace, TRACE_EVENT_TOOL_CALL_FAILED)
    all_calls = (*requested, *succeeded, *failed)

    return ToolMisuseSolutionState(
        trace=trace,
        learner_prompts=trace.of_family_and_type(
            family="learner", event_type="USER_PROMPT_SUBMITTED"
        ),
        requested_tool_calls=requested,
        successful_tool_calls=succeeded,
        failed_tool_calls=failed,
        file_reads=tuple(call for call in all_calls if call.tool_name == "read_file"),
        file_deletes=tuple(
            call for call in all_calls if call.tool_name == "delete_file"
        ),
    )


def build_code_execution_solution_state(
    trace: TraceIndex,
) -> CodeExecutionSolutionState:
    succeeded = _tool_calls(trace, TRACE_EVENT_TOOL_CALL_SUCCEEDED)
    return CodeExecutionSolutionState(
        trace=trace,
        successful_tool_calls=succeeded,
        execution_tool_calls=tuple(
            call for call in succeeded if call.tool_name in EXECUTION_TOOL_NAMES
        ),
    )


def build_memory_poisoning_solution_state(
    trace: TraceIndex,
) -> MemoryPoisoningSolutionState:
    requested = _tool_calls(trace, TRACE_EVENT_TOOL_CALL_REQUESTED)
    succeeded = _tool_calls(trace, TRACE_EVENT_TOOL_CALL_SUCCEEDED)
    failed = _tool_calls(trace, TRACE_EVENT_TOOL_CALL_FAILED)
    completed_calls = (*succeeded, *failed)

    return MemoryPoisoningSolutionState(
        trace=trace,
        requested_tool_calls=requested,
        successful_tool_calls=succeeded,
        failed_tool_calls=failed,
        memory_writes=tuple(
            call for call in completed_calls if call.tool_name == "write_memory"
        ),
        memory_retrievals=tuple(
            call for call in completed_calls if call.tool_name == "retrieve_memory"
        ),
        invoice_payment_calls=tuple(
            call for call in completed_calls if call.tool_name == "pay_invoice"
        ),
    )
