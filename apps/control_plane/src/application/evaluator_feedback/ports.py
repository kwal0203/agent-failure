from typing import Protocol
from uuid import UUID

from .types import EvaluatorPersistedResult


class EvaluatorPort(Protocol):
    def list_results_for_session(
        self, session_id: UUID
    ) -> list[EvaluatorPersistedResult]: ...
