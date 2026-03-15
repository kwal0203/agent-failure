class SessionLoopProviderFailureError(Exception):
    def __init__(
        self, message: str = "Provider failure", details: dict[str, str] | None = None
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class SessionLoopInvalidRequestError(Exception):
    def __init__(
        self, message: str = "Invalid request", details: dict[str, str] | None = None
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class SessionLoopInternalError(Exception):
    def __init__(
        self, message: str = "Internal error", details: dict[str, str] | None = None
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
