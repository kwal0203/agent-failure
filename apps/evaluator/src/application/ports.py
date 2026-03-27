from typing import Protocol
from uuid import UUID

from .types import EvaluatorRunResult, EvaluatorTaskInput, EvaluatorFinding


class EvaluatorPort(Protocol):
    def evaluate_trace_window(
        self, input: EvaluatorTaskInput
    ) -> EvaluatorRunResult: ...

    def persist_result_if_new(
        self,
        idempo_key: str,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        evaluator_version: int,
        finding: EvaluatorFinding,
    ) -> bool: ...
