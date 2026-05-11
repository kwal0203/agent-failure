from typing import Protocol
from uuid import UUID

from .types import ClassCodeRecord, EnrollmentTokenRecord


class EnrollmentRepositoryPort(Protocol):
    def get_class_code(self, code: str) -> ClassCodeRecord | None: ...

    def create_enrollment_token(
        self,
        *,
        nonce: str,
        email: str,
        course_id: str,
        course_name: str,
        expires_at_epoch_sec: int,
    ) -> None: ...

    def increment_class_code_uses(self, code: str) -> None: ...

    def get_enrollment_token(self, nonce: str) -> EnrollmentTokenRecord | None: ...

    def is_user_enrolled(self, *, user_id: UUID, course_id: str) -> bool: ...

    def mark_enrollment_token_redeemed(self, nonce: str) -> None: ...

    def create_enrollment(
        self,
        *,
        user_sub: str,
        user_id: UUID,
        email: str,
        course_id: str,
        course_name: str,
    ) -> None: ...

    def commit(self) -> None: ...
