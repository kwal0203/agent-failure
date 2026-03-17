from typing import Any


class RuntimeImageResolutionError(Exception):
    def __init__(
        self,
        message: str = "Runtime image resolution failed.",
        details: dict[str, Any] | None = None,
    ) -> None:
        self._message = message
        self._details = details or {}
        super().__init__(self._message)


class ImageNotFoundError(RuntimeImageResolutionError):
    def __init__(
        self,
        lab_slug: str,
        lab_version: str,
    ) -> None:
        super().__init__(
            message="Runtime image not found for requested lab version",
            details={"lab_slug": lab_slug, "lab_version": lab_version},
        )


class ImageRevokedError(RuntimeImageResolutionError):
    def __init__(self, lab_slug: str, lab_version: str, status: str) -> None:
        super().__init__(
            message="Requested runtime image is not active.",
            details={
                "lab_slug": lab_slug,
                "lab_version": lab_version,
                "status": status,
            },
        )


class DefaultSelectionError(RuntimeImageResolutionError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, details=details)


class InvalidImageLockError(RuntimeImageResolutionError):
    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message=message, details=details)
