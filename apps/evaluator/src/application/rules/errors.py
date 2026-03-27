from uuid import UUID


class UnsupportedLabBundleError(Exception):
    def __init__(
        self,
        lab_id: UUID,
        lab_version_id: UUID,
        evaluator_version: int,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        self.lab_id = lab_id
        self.lab_version_id = lab_version_id
        self.evaluator_version = evaluator_version
        self.message = message
        self.details = details or {
            "lab_id": lab_id,
            "lab_version_id": lab_version_id,
            "evaluator_version": evaluator_version,
            "message": message,
        }
        super().__init__(self.message)
