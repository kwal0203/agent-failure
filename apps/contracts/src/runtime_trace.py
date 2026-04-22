from typing import TypeAlias, Literal

from .types import TraceFamily


ALLOWED_EVENT_TYPES: dict[TraceFamily, set[str]] = {
    "lifecycle": {"SESSION_CREATED", "SESSION_TRANSITIONED"},
    "learner": {
        "USER_PROMPT_SUBMITTED",
        "ATTACK_EMAIL_SENT",
        "BENIGN_EMAIL_SENT",
        "LEARNER_EXPLANATION_SUBMITTED",
    },
    "runtime": {
        "RUNTIME_PROVISION_REQUESTED",
        "RUNTIME_PROVISION_ACCEPTED",
        "RUNTIME_PROVISION_PENDING",
        "RUNTIME_PROVISION_FAILED",
        "RUNTIME_HEALTH_STATUS",
        "ATTACK_EMAIL_SENT",
        "MALICIOUS_EMAIL_READ",
        "TOKEN_DISCLOSURE_ATTEMPTED",
        "TOKEN_DISCLOSED",
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
    ("learner", "ATTACK_EMAIL_SENT"): {"email_from", "subject"},
    ("learner", "BENIGN_EMAIL_SENT"): {"email_from", "subject"},
    ("learner", "LEARNER_EXPLANATION_SUBMITTED"): {"type", "explanation_id", "source"},
    ("runtime", "ATTACK_EMAIL_SENT"): {"email_id", "recipient", "subject"},
    ("runtime", "MALICIOUS_EMAIL_READ"): {"email_id", "subject", "malicious_marker"},
    ("runtime", "TOKEN_DISCLOSURE_ATTEMPTED"): {"channel", "target"},
    ("runtime", "TOKEN_DISCLOSED"): {"channel", "token_kind"},
    ("tool", "TOOL_CALL_REQUESTED"): {"tool_name"},
    ("tool", "TOOL_CALL_SUCCEEDED"): {"tool_name"},
    ("tool", "TOOL_CALL_FAILED"): {"tool_name"},
    ("model", "MODEL_TURN_FAILED"): {"provider", "error_code"},
    # ("lifecycle", "SESSION_CREATED"): set(),
    # ("lifecycle", "SESSION_TRANSITIONED"): set(),
    # ("learner", "USER_PROMPT_SUBMITTED"): set(),
    # ("runtime", "RUNTIME_PROVISION_REQUESTED"): set(),
    # ("runtime", "RUNTIME_PROVISION_ACCEPTED"): set(),
    # ("runtime", "RUNTIME_HEALTH_STATUS"): set(),
    # ("tool", "TOOL_CALL_REQUESTED"): set(),
    # ("tool", "TOOL_CALL_SUCCEEDED"): set(),
    # ("model", "MODEL_TURN_STARTED"): set(),
    # ("model", "MODEL_CHUNK_EMITTED"): set(),
    # ("model", "MODEL_TURN_COMPLETED"): set(),
}

RuntimeTraceEventType: TypeAlias = Literal[
    "ATTACK_EMAIL_SENT",
    "MALICIOUS_EMAIL_READ",
    "TOKEN_DISCLOSURE_ATTEMPTED",
    "TOKEN_DISCLOSED",
    "TOOL_CALL_REQUESTED",
    "TOOL_CALL_SUCCEEDED",
    "TOOL_CALL_FAILED",
]


# @dataclass(frozen=True, slots=True)
# class RuntimeTraceEvent:
#     session_id: UUID
#     lab_id: UUID
#     lab_version_id: UUID
#     family: TraceFamily
#     event_type: RuntimeTraceEventType
#     payload: RuntimePayload
#     occurred_at: datetime | None = None
#     correlation_id: str | None = None
#     request_id: str | None = None
#     actor_user_id: UUID | None = None


REQUIRED_PAYLOAD_KEYS_BY_EVENT_TYPE: dict[RuntimeTraceEventType, tuple[str, ...]] = {
    "ATTACK_EMAIL_SENT": ("email_id", "recipient", "subject"),
    "MALICIOUS_EMAIL_READ": ("email_id", "subject", "malicious_marker"),
    "TOKEN_DISCLOSURE_ATTEMPTED": ("channel", "target"),
    "TOKEN_DISCLOSED": ("channel", "token_kind"),
    "TOOL_CALL_REQUESTED": ("tool_name",),
    "TOOL_CALL_SUCCEEDED": ("tool_name",),
    "TOOL_CALL_FAILED": ("tool_name",),
}
