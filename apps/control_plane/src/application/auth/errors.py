class AuthTokenInvalidError(Exception):
    def __init__(
        self,
        code: str = "AUTH_TOKEN_INVALID",
        message: str = "Authentication token is invalid.",
        details: dict[str, object] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AuthTokenExpiredError(Exception):
    def __init__(
        self,
        code: str = "AUTH_TOKEN_EXPIRED",
        message: str = "Authentication token is expired.",
        details: dict[str, object] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
