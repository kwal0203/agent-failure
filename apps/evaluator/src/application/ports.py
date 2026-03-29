from typing import Protocol
from uuid import UUID
from datetime import datetime

from .types import (
    EvaluatorTaskInput,
    EvaluatorFinding,
    EvaluatorTraceEvent,
    EvaluatorLabRuntimeBinding,
    EvaluatorPersistedResult,
    PendingEvaluatorEvent,
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

    def list_results_for_session(
        self, session_id: UUID
    ) -> list[EvaluatorPersistedResult]: ...


class EvaluatorLabLookupPort(Protocol):
    def get_runtime_binding(
        self, lab_id: UUID, lab_version_id: UUID
    ) -> EvaluatorLabRuntimeBinding: ...


class EvaluatorOutboxRepository(Protocol):
    def claim_pending_evaluate(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingEvaluatorEvent]: ...

    def mark_processed(
        self, *, outbox_event_id: UUID, processed_at: datetime | None = None
    ) -> None: ...

    def mark_terminal_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        failed_at: datetime | None = None,
    ) -> None: ...
