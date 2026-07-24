from uuid import UUID


class UnsupportedLabBundleError(Exception):
    def __init__(
        self,
        lab_id: UUID,
        lab_version_id: UUID,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        self.lab_id = lab_id
        self.lab_version_id = lab_version_id
        self.message = message
        self.details = details or {
            "lab_id": lab_id,
            "lab_version_id": lab_version_id,
            "message": message,
        }
        super().__init__(self.message)
