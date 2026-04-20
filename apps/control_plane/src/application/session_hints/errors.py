class ForbiddenErrorSessionHints(Exception):
    def __init__(self, role: str) -> None:
        self.role = role
        self.message = "forbidden: principal cannot update session hints"
        self.details: dict[str, object] = {"role": role}
        super().__init__(self.message)


class SessionNotFoundErrorSessionHints(Exception):
    def __init__(self) -> None:
        self.message = "session not found"
        self.details: dict[str, object] = {}
        super().__init__(self.message)
