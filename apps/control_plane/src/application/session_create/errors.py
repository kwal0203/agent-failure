from uuid import UUID


class LabNotAvailableError(Exception):
    def __init__(
        self,
        lab_id: UUID,
        message: str = "Requested lab is not available.",
        details: dict[str, object] | None = None,
    ) -> None:
        self.lab_id = lab_id
        self.message = message
        self.details = details or {"lab_id": str(lab_id)}
        super().__init__(self.message)


class QuotaExceededError(Exception):
    def __init__(
        self,
        current: int,
        quota: int,
        message: str = "You have exceeded your quota.",
        details: dict[str, object] | None = None,
    ) -> None:
        self.current = current
        self.quota = quota
        self.message = message
        self.details = details or {"current": current, "quota": quota}
        super().__init__(self.message)


class RateLimitedError(Exception):
    def __init__(
        self,
        limit: int,
        message: str = "You have been rate limited.",
        details: dict[str, object] | None = None,
    ) -> None:
        self.limit = limit
        self.message = message
        self.details = details or {"limit": limit}
        super().__init__(self.message)


class DegradedModeRestrictionError(Exception):
    def __init__(
        self,
        message: str = "You are in degraded mode.",
        details: dict[str, object] | None = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class InvalidIdempotencyKeyError(Exception):
    def __init__(
        self,
        idem_key: str,
        message: str = "Invalid idempotency key.",
        details: dict[str, object] | None = None,
    ) -> None:
        self.idem_key = idem_key
        self.message = message
        self.details = details or {"idem_key": idem_key}
        super().__init__(self.message)


class ForbiddenError(Exception):
    def __init__(
        self,
        role: str,
        message: str = "You are not authorized.",
        details: dict[str, object] | None = None,
    ) -> None:
        self.role = role
        self.message = message
        self.details = details or {"role": role}
        super().__init__(self.message)


class AdmissionDecisionError(Exception):
    def __init__(
        self,
        code: str | None,
        message: str = "You are not authorized.",
        details: dict[str, object] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"Unhandled admission denial code: {code}")


class DuplicateIdempotencyKeyError(Exception):
    def __init__(
        self,
        code: str | None,
        message: str = "You are not authorized.",
        details: dict[str, object] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__("Duplicate idempotency key detected.")
