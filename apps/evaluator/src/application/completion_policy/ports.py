from datetime import datetime
from typing import Protocol

from .types import CompletionPolicyDecision, CompletionPolicyInput


class SessionCompletionPolicyPort(Protocol):
    def evaluate(
        self,
        *,
        input: CompletionPolicyInput,
        evaluated_at: datetime | None = None,
    ) -> CompletionPolicyDecision: ...
