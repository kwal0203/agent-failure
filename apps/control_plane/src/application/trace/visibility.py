from .types import TraceFamily


LEARNER_VISIBLE_ALLOWLIST: set[tuple[TraceFamily, str]] = {
    ("learner", "USER_PROMPT_SUBMITTED"),
    ("model", "MODEL_TURN_COMPLETED"),
    ("model", "MODEL_TURN_FAILED"),
}
