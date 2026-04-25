from typing import Protocol

from .types import (
    AuthorityBulletinClassificationInput,
    AuthorityBulletinClassificationResult,
)


class AuthorityBulletinClassifierPort(Protocol):
    async def classify_prompt(
        self, *, input: AuthorityBulletinClassificationInput
    ) -> AuthorityBulletinClassificationResult: ...
