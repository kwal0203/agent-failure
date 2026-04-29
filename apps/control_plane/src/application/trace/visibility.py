from .types import TraceFamily


LEARNER_VISIBLE_ALLOWLIST: set[tuple[TraceFamily, str]] = {
    ("lifecycle", "SESSION_CREATED"),
    ("learner", "USER_PROMPT_SUBMITTED"),
    ("learner", "ATTACK_EMAIL_SENT"),
    ("runtime", "RUNTIME_PROVISION_REQUESTED"),
    ("runtime", "RUNTIME_PROVISION_ACCEPTED"),
    ("runtime", "RUNTIME_PROVISION_FAILED"),
    ("runtime", "TRY_ATTACK_CONSOLE_HINT"),
    ("runtime", "ATTACK_EMAIL_SENT"),
    ("runtime", "MALICIOUS_EMAIL_READ"),
    ("runtime", "TOKEN_DISCLOSURE_ATTEMPTED"),
    ("runtime", "TOKEN_DISCLOSED"),
    ("tool", "TOOL_CALL_REQUESTED"),
    ("tool", "TOOL_CALL_SUCCEEDED"),
    ("tool", "TOOL_CALL_FAILED"),
    ("model", "MODEL_TURN_COMPLETED"),
    ("model", "MODEL_TURN_FAILED"),
}
