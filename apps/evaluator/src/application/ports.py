from typing import Protocol
from uuid import UUID

from .types import (
    EvaluatorTaskInput,
    EvaluatorFinding,
    EvaluatorTraceEvent,
    EvaluatorLabRuntimeBinding,
)


class EvaluatorPort(Protocol):
    def persist_result_if_new(
        self,
        idempo_key: str,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        evaluator_version: int,
        finding: EvaluatorFinding,
    ) -> bool: ...

    def load_events(self, input: EvaluatorTaskInput) -> list[EvaluatorTraceEvent]: ...


class EvaluatorLabLookupPort(Protocol):
    def get_runtime_binding(
        self, lab_id: UUID, lab_version_id: UUID
    ) -> EvaluatorLabRuntimeBinding: ...
