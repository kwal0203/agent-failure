from dataclasses import dataclass


@dataclass(frozen=True)
class ProvisioningPolicy:
    readiness_timeout_seconds: float = 30.0
    readiness_poll_interval_seconds: float = 0.1
    retry_backoff_seconds: int = 15


@dataclass(frozen=True)
class CleanupPolicy:
    max_attempts: int = 3
    retry_backoff_seconds: int = 15
    already_gone_reverify_backoff_seconds: int = 5


@dataclass(frozen=True)
class ExpiryPolicy:
    """Absolute lifetime limits.

    Inactivity is deliberately not inferred from session timestamps. An idle
    policy requires a persisted last-activity timestamp maintained by every
    interaction path; until that exists, only authoritative timestamps expire
    sessions.
    """

    provisioning_timeout_seconds: int = 900
    max_session_lifetime_seconds: int = 86_400
