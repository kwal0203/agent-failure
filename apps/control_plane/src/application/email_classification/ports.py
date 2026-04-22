from typing import Protocol

from .types import EmailClassificationInput, EmailClassificationResult


class EmailMaliciousnessClassifierPort(Protocol):
    async def classify_email(
        self, *, input: EmailClassificationInput
    ) -> EmailClassificationResult: ...
