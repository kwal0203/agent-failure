from typing import Protocol

from .types import (
    EvaluatorRunResult,
    EvaluatorTaskInput,
)


class EvaluatorPort(Protocol):
    def evaluate_trace_window(
        self, input: EvaluatorTaskInput
    ) -> EvaluatorRunResult: ...
