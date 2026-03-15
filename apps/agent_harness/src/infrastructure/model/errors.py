class ProviderAuthError(Exception):
    def __init__(
        self,
        message: str = "Provider authentication error",
        details: dict[str, str] | None = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ProviderTimeoutError(Exception):
    def __init__(
        self,
        message: str = "Provider timeout error",
        details: dict[str, str] | None = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ProviderResponseError(Exception):
    def __init__(
        self,
        message: str = "Provider response error",
        details: dict[str, str] | None = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ProviderUnavailableError(Exception):
    def __init__(
        self,
        message: str = "Provider unavailable error",
        details: dict[str, str] | None = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
