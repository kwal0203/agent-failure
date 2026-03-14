class ForbiddenErrorSessionQuery(Exception):
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
