from typing import TypeAlias, Literal

from .types import TraceFamily


ALLOWED_EVENT_TYPES: dict[TraceFamily, set[str]] = {
    "lifecycle": {"SESSION_CREATED", "SESSION_TRANSITIONED"},
    "learner": {
        "USER_PROMPT_SUBMITTED",
        "ATTACK_EMAIL_SENT",
        "LEARNER_EXPLANATION_SUBMITTED",
    },
    "runtime": {
        "RUNTIME_PROVISION_REQUESTED",
        "RUNTIME_PROVISION_ACCEPTED",
        "RUNTIME_PROVISION_PENDING",
        "RUNTIME_PROVISION_FAILED",
        "RUNTIME_HEALTH_STATUS",
        "TRY_ATTACK_CONSOLE_HINT",
        "ATTACK_EMAIL_SENT",
        "MALICIOUS_EMAIL_READ",
        "TOKEN_DISCLOSURE_ATTEMPTED",
        "TOKEN_DISCLOSED",
        "SIMULATED_TELEMETRY_SIGNAL",
    },
    "tool": {"TOOL_CALL_REQUESTED", "TOOL_CALL_SUCCEEDED", "TOOL_CALL_FAILED"},
    "model": {
        "MODEL_TURN_STARTED",
        "MODEL_CHUNK_EMITTED",
        "MODEL_TURN_COMPLETED",
        "MODEL_TURN_FAILED",
    },
}

REQUIRED_PAYLOAD_FIELDS: dict[tuple[TraceFamily, str], set[str]] = {
    ("runtime", "RUNTIME_PROVISION_FAILED"): {"reason_code"},
    ("runtime", "RUNTIME_PROVISION_PENDING"): {
        "reason_code",
        "phase",
        "ready",
        "exists",
        "outbox_event_id",
        "attempt_count",
    },
    ("learner", "ATTACK_EMAIL_SENT"): {
        "email_id",
        "email_from",
        "subject",
        "malicious_marker",
    },
    ("learner", "LEARNER_EXPLANATION_SUBMITTED"): {"type", "explanation_id", "source"},
    ("runtime", "TRY_ATTACK_CONSOLE_HINT"): {"message"},
    ("runtime", "ATTACK_EMAIL_SENT"): {"email_id", "recipient", "subject"},
    ("runtime", "MALICIOUS_EMAIL_READ"): {"email_id", "subject", "malicious_marker"},
    ("runtime", "TOKEN_DISCLOSURE_ATTEMPTED"): {"channel", "target"},
    ("runtime", "TOKEN_DISCLOSED"): {"channel", "token_kind"},
    ("runtime", "SIMULATED_TELEMETRY_SIGNAL"): {
        "signal_id",
        "section",
        "severity",
        "message",
        "simulated",
    },
    ("tool", "TOOL_CALL_REQUESTED"): {"tool_name"},
    ("tool", "TOOL_CALL_SUCCEEDED"): {"tool_name"},
    ("tool", "TOOL_CALL_FAILED"): {"tool_name"},
    ("model", "MODEL_TURN_FAILED"): {"provider", "error_code"},
}

RuntimeTraceEventType: TypeAlias = Literal[
    "TRY_ATTACK_CONSOLE_HINT",
    "ATTACK_EMAIL_SENT",
    "MALICIOUS_EMAIL_READ",
    "TOKEN_DISCLOSURE_ATTEMPTED",
    "TOKEN_DISCLOSED",
    "SIMULATED_TELEMETRY_SIGNAL",
    "TOOL_CALL_REQUESTED",
    "TOOL_CALL_SUCCEEDED",
    "TOOL_CALL_FAILED",
]
REQUIRED_PAYLOAD_KEYS_BY_EVENT_TYPE: dict[RuntimeTraceEventType, tuple[str, ...]] = {
    "TRY_ATTACK_CONSOLE_HINT": ("message",),
    "ATTACK_EMAIL_SENT": ("email_id", "recipient", "subject"),
    "MALICIOUS_EMAIL_READ": ("email_id", "subject", "malicious_marker"),
    "TOKEN_DISCLOSURE_ATTEMPTED": ("channel", "target"),
    "TOKEN_DISCLOSED": ("channel", "token_kind"),
    "SIMULATED_TELEMETRY_SIGNAL": (
        "signal_id",
        "section",
        "severity",
        "message",
        "simulated",
    ),
    "TOOL_CALL_REQUESTED": ("tool_name",),
    "TOOL_CALL_SUCCEEDED": ("tool_name",),
    "TOOL_CALL_FAILED": ("tool_name",),
}
