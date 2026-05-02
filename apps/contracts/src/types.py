from typing import Literal, TypeAlias, Mapping


TraceFamily = Literal["lifecycle", "learner", "runtime", "tool", "model"]

SessionCompletedEventName = Literal["session.completed.v1"]
SessionFeedbackCreatedEventName = Literal["session.feedback.created.v1"]
CompletionOutcome = Literal["completed_success", "completed_failure"]
FeedbackSeverity = Literal["info", "warning", "error"]
OutboxEventName = Literal["session.completed.v1", "session.feedback.created.v1"]

# Shared outbox event names across control-plane/evaluator.
OUTBOX_EVENT_SESSION_TRANSITIONED = "session.transitioned.v1"
OUTBOX_EVENT_SESSION_PROVISIONING = "session.provisioning.v1"
OUTBOX_EVENT_SESSION_CLEANUP_REQUESTED = "session.cleanup.requested.v1"
OUTBOX_EVENT_SESSION_EVALUATE_REQUESTED = "session.evaluate.requested.v1"
OUTBOX_EVENT_SESSION_PUBLISH_FEEDBACK = "session.publish.feedback.v1"
OUTBOX_EVENT_SESSION_OBJECTIVE_COMPLETED = "session.objective.completed.v1"
OUTBOX_EVENT_SESSION_HINT_UNLOCKED = "session.hint.unlocked.v1"
OUTBOX_EVENT_SESSION_COMPLETED = "session.completed.v1"
OUTBOX_EVENT_SESSION_FEEDBACK_CREATED = "session.feedback.created.v1"

# Shared runtime/tool trace event names across control-plane/evaluator.
TRACE_EVENT_ATTACK_EMAIL_SENT = "ATTACK_EMAIL_SENT"
TRACE_EVENT_MALICIOUS_EMAIL_READ = "MALICIOUS_EMAIL_READ"
TRACE_EVENT_TOKEN_DISCLOSURE_ATTEMPTED = "TOKEN_DISCLOSURE_ATTEMPTED"
TRACE_EVENT_TOKEN_DISCLOSED = "TOKEN_DISCLOSED"
TRACE_EVENT_TOOL_CALL_REQUESTED = "TOOL_CALL_REQUESTED"
TRACE_EVENT_TOOL_CALL_SUCCEEDED = "TOOL_CALL_SUCCEEDED"
TRACE_EVENT_TOOL_CALL_FAILED = "TOOL_CALL_FAILED"


JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | list["JSONValue"] | dict[str, "JSONValue"]
RuntimePayload: TypeAlias = Mapping[str, JSONValue]


# Canonical runtime tool contract shared across runtime/control-plane/evaluator.
ToolName = Literal[
    "list_tools",
    "list_files",
    "list_inbox",
    "read_email",
    "read_file",
    "write_file",
    "delete_file",
    "follow_runbook",
    "read_invoice",
    "lookup_vendor_master",
    "retrieve_memory",
    "write_memory",
    "pay_invoice",
]

CANONICAL_TOOL_ARGS_REQUIRED: Mapping[ToolName, tuple[str, ...]] = {
    "list_tools": (),
    "list_files": (),
    "list_inbox": (),
    "read_email": ("email_id",),
    "read_file": ("path",),
    "write_file": ("path", "content"),
    "delete_file": ("path",),
    "follow_runbook": ("incident_type",),
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
