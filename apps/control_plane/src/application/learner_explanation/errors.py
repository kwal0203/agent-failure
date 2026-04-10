class InvalidLearnerExplanationError(Exception):
    def __init__(
        self,
        code: str = "INVALID_LEARNER_EXPLANATION",
        message: str = "Learner explanation input is invalid.",
        details: dict[str, object] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)
