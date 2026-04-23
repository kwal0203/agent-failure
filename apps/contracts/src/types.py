from typing import Literal, TypeAlias, Mapping


TraceFamily = Literal["lifecycle", "learner", "runtime", "tool", "model"]

SessionCompletedEventName = Literal["session.completed.v1"]
SessionFeedbackCreatedEventName = Literal["session.feedback.created.v1"]
CompletionOutcome = Literal["completed_success", "completed_failure"]
FeedbackSeverity = Literal["info", "warning", "error"]
OutboxEventName = Literal["session.completed.v1", "session.feedback.created.v1"]


JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
RuntimePayload: TypeAlias = Mapping[str, JSONValue]


# Canonical runtime tool contract shared across runtime/control-plane/evaluator.
ToolName = Literal[
    "list_inbox",
    "read_email",
    "read_file",
    "delete_file",
    "read_invoice",
    "lookup_vendor_master",
    "retrieve_memory",
    "write_memory",
    "pay_invoice",
]

CANONICAL_TOOL_ARGS_REQUIRED: Mapping[ToolName, tuple[str, ...]] = {
    "list_inbox": (),
    "read_email": ("email_id",),
    "read_file": ("path",),
    "delete_file": ("path",),
    # NOTE(lab3): Runtime v1 supports invoice_id | invoice_document, but the
    # current classifier contract validates exact required keys only. Keep
    # invoice_id as the canonical minimum until validator supports either/or.
    "read_invoice": ("invoice_id",),
    "lookup_vendor_master": ("vendor_name",),
    "retrieve_memory": ("query",),
    # NOTE(lab3): metadata is currently represented as a string in classifier
    # args; runtime handlers can parse/expand this later.
    "write_memory": ("memory_type", "content", "metadata"),
    "pay_invoice": ("vendor_name", "account_number", "amount", "invoice_id"),
}
