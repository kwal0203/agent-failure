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


class DuplicateIdempotencyKeyError(Exception):
    def __init__(
        self,
        code: str,
        message: str = "Duplicate idempotency key.",
        details: dict[str, object] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__("Duplicate idempotency key detected.")
