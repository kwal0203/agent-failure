class ForbiddenErrorSessionReportEvidence(Exception):
    def __init__(self, role: str) -> None:
        self.role = role
        self.message = "forbidden: principal cannot access session report evidence"
        self.details: dict[str, object] = {"role": role}
        super().__init__(self.message)


class SessionNotFoundErrorSessionReportEvidence(Exception):
    def __init__(self) -> None:
        self.message = "session not found"
        self.details: dict[str, object] = {}
        super().__init__(self.message)


class InvalidSessionReportEvidenceError(Exception):
    def __init__(self, *, message: str, details: dict[str, object]) -> None:
        self.message = message
        self.details = details
        super().__init__(self.message)
