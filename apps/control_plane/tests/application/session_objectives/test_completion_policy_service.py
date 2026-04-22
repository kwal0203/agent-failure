from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

from apps.contracts.src.types import CompletionOutcome
from apps.control_plane.src.application.session_completion.guard import (
    evaluate_completion_transition,
)
from apps.control_plane.src.application.session_completion.types import (
    CompletionStatus,
)
from apps.control_plane.src.application.session_objectives.service import (
    process_pending_objective_completed_once,
)
from apps.control_plane.src.application.session_objectives.types import (
    PendingSessionObjectiveCompletedEvent,
)


class _FakeTemplateReader:
    def __init__(self, templates: list[tuple[str, str, int]]) -> None:
        self._templates = templates

    def list_objective_templates(
        self, lab_version_id: UUID
    ) -> list[tuple[str, str, int]]:
        _ = lab_version_id
        return list(self._templates)


class _FakeObjectiveWriter:
    def __init__(self, statuses: dict[str, str]) -> None:
        self._statuses = dict(statuses)

    def upsert_objective(
        self,
        session_id: UUID,
        objective_key: str,
        label: str,
        sort_order: int,
    ) -> None:
        _ = (session_id, objective_key, label, sort_order)

    def mark_complete(
        self,
        *,
        session_id: UUID,
        objective_key: str,
        completed_at: datetime | None = None,
    ) -> None:
        _ = (session_id, completed_at)
        self._statuses[objective_key] = "complete"

    def list_objective_states(self, *, session_id: UUID) -> list[tuple[str, str]]:
        _ = session_id
        return list(self._statuses.items())


@dataclass
class _CompletionWriteCall:
    session_id: UUID
    completion_status: CompletionStatus
    completed_at: datetime
    completion_reason_code: str | None
    applied: bool
    decision_reason: str


class _FakeCompletionWriter:
    def __init__(self) -> None:
        self.current_status: CompletionStatus = "in_progress"
        self.current_completed_at: datetime | None = None
        self.current_reason_code: str | None = None
        self.calls: list[_CompletionWriteCall] = []

    def mark_completion_if_in_progress(
        self,
        *,
        session_id: UUID,
        completion_status: CompletionStatus,
        completed_at: datetime,
        completion_reason_code: str | None,
    ) -> bool:
        decision = evaluate_completion_transition(
            current_status=self.current_status,
            requested_status=completion_status,
        )
        applied = decision.should_apply
        if applied:
            self.current_status = completion_status
            self.current_completed_at = completed_at
            self.current_reason_code = completion_reason_code
        self.calls.append(
            _CompletionWriteCall(
                session_id=session_id,
                completion_status=completion_status,
                completed_at=completed_at,
                completion_reason_code=completion_reason_code,
                applied=applied,
                decision_reason=decision.reason,
            )
        )
        return applied


class _FakeOutbox:
    def __init__(self, events: list[PendingSessionObjectiveCompletedEvent]) -> None:
        self._events = list(events)
        self.processed_ids: list[UUID] = []
        self.retryable_failures: list[UUID] = []
        self.terminal_failures: list[UUID] = []

    def claim_pending_objective_completed(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingSessionObjectiveCompletedEvent]:
        _ = now
        claimed = self._events[:limit]
        self._events = self._events[limit:]
        return claimed

    def mark_processed(
        self, *, outbox_event_id: UUID, processed_at: datetime | None = None
    ) -> None:
        _ = processed_at
        self.processed_ids.append(outbox_event_id)

    def mark_retryable_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        backoff_seconds: int = 15,
        failed_at: datetime | None = None,
    ) -> None:
        _ = (error_message, backoff_seconds, failed_at)
        self.retryable_failures.append(outbox_event_id)

    def mark_terminal_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        failed_at: datetime | None = None,
    ) -> None:
        _ = (error_message, failed_at)
        self.terminal_failures.append(outbox_event_id)


class _FakeCompletionEventOutbox:
    def enqueue_session_completed(
        self,
        *,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        outcome: CompletionOutcome,
        completion_reason_code: str | None,
        trigger_event_index: int | None,
        idempotency_key: str,
        occurred_at: datetime | None = None,
    ) -> None:
        _ = (
            session_id,
            lab_id,
            lab_version_id,
            outcome,
            completion_reason_code,
            trigger_event_index,
            idempotency_key,
            occurred_at,
        )


def _build_event(
    *,
    outbox_event_id: UUID,
    session_id: UUID,
    lab_id: UUID,
    lab_version_id: UUID,
    objective_key: str,
    reason_code: str,
    trigger_event_index: int,
    occurred_at: datetime,
) -> PendingSessionObjectiveCompletedEvent:
    return PendingSessionObjectiveCompletedEvent(
        outbox_event_id=outbox_event_id,
        session_id=session_id,
        payload={
            "session_id": str(session_id),
            "lab_id": str(lab_id),
            "lab_version_id": str(lab_version_id),
            "objective_key": objective_key,
            "reason_code": reason_code,
            "trigger_event_index": trigger_event_index,
            "occurred_at": occurred_at.isoformat(),
            "idempotency_key": (
                f"objective:{session_id}:{objective_key}:{trigger_event_index}"
            ),
            "source": "evaluator",
            "evaluator_version": 1,
        },
        attempt_count=0,
        requested_at=occurred_at,
    )


def test_completion_policy_all_required_complete_marks_completed_success() -> None:
    session_id = uuid4()
    lab_id = uuid4()
    lab_version_id = uuid4()
    occurred_at = datetime(2026, 4, 22, 18, 5, 0, tzinfo=timezone.utc)
    outbox = _FakeOutbox(
        events=[
            _build_event(
                outbox_event_id=uuid4(),
                session_id=session_id,
                lab_id=lab_id,
                lab_version_id=lab_version_id,
                objective_key="obj_a",
                reason_code="RULE_A",
                trigger_event_index=11,
                occurred_at=occurred_at,
            ),
            _build_event(
                outbox_event_id=uuid4(),
                session_id=session_id,
                lab_id=lab_id,
                lab_version_id=lab_version_id,
                objective_key="obj_b",
                reason_code="RULE_B",
                trigger_event_index=12,
                occurred_at=occurred_at,
            ),
        ]
    )
    template_reader = _FakeTemplateReader(
        [("obj_a", "Objective A", 0), ("obj_b", "Objective B", 1)]
    )
    objective_writer = _FakeObjectiveWriter({"obj_a": "pending", "obj_b": "pending"})
    completion_writer = _FakeCompletionWriter()

    result = process_pending_objective_completed_once(
        outbox_repo=outbox,
        event_outbox_repo=_FakeCompletionEventOutbox(),
        template_reader=template_reader,
        objective_writer=objective_writer,
        completion_writer=completion_writer,
    )

    assert result.claimed_count == 2
    assert result.succeeded_count == 2
    assert completion_writer.current_status == "completed_success"
    assert completion_writer.current_reason_code == "ALL_REQUIRED_OBJECTIVES_COMPLETED"
    assert completion_writer.current_completed_at == occurred_at
    assert len(completion_writer.calls) == 1
    assert completion_writer.calls[0].applied is True


def test_completion_policy_missing_required_objective_keeps_in_progress() -> None:
    session_id = uuid4()
    lab_id = uuid4()
    lab_version_id = uuid4()
    occurred_at = datetime(2026, 4, 22, 18, 10, 0, tzinfo=timezone.utc)
    outbox = _FakeOutbox(
        events=[
            _build_event(
                outbox_event_id=uuid4(),
                session_id=session_id,
                lab_id=lab_id,
                lab_version_id=lab_version_id,
                objective_key="obj_a",
                reason_code="RULE_A",
                trigger_event_index=21,
                occurred_at=occurred_at,
            )
        ]
    )
    template_reader = _FakeTemplateReader(
        [("obj_a", "Objective A", 0), ("obj_b", "Objective B", 1)]
    )
    objective_writer = _FakeObjectiveWriter({"obj_a": "pending", "obj_b": "pending"})
    completion_writer = _FakeCompletionWriter()

    result = process_pending_objective_completed_once(
        outbox_repo=outbox,
        event_outbox_repo=_FakeCompletionEventOutbox(),
        template_reader=template_reader,
        objective_writer=objective_writer,
        completion_writer=completion_writer,
    )

    assert result.claimed_count == 1
    assert result.succeeded_count == 1
    assert completion_writer.current_status == "in_progress"
    assert completion_writer.current_reason_code is None
    assert completion_writer.current_completed_at is None
    assert completion_writer.calls == []


def test_completion_policy_replay_is_idempotent_for_terminal_write() -> None:
    session_id = uuid4()
    lab_id = uuid4()
    lab_version_id = uuid4()
    occurred_at = datetime(2026, 4, 22, 18, 20, 0, tzinfo=timezone.utc)
    replay_at = datetime(2026, 4, 22, 18, 21, 0, tzinfo=timezone.utc)
    template_reader = _FakeTemplateReader([("obj_a", "Objective A", 0)])
    objective_writer = _FakeObjectiveWriter({"obj_a": "pending"})
    completion_writer = _FakeCompletionWriter()

    first_outbox = _FakeOutbox(
        events=[
            _build_event(
                outbox_event_id=uuid4(),
                session_id=session_id,
                lab_id=lab_id,
                lab_version_id=lab_version_id,
                objective_key="obj_a",
                reason_code="RULE_A",
                trigger_event_index=31,
                occurred_at=occurred_at,
            )
        ]
    )
    first_result = process_pending_objective_completed_once(
        outbox_repo=first_outbox,
        event_outbox_repo=_FakeCompletionEventOutbox(),
        template_reader=template_reader,
        objective_writer=objective_writer,
        completion_writer=completion_writer,
    )

    replay_outbox = _FakeOutbox(
        events=[
            _build_event(
                outbox_event_id=uuid4(),
                session_id=session_id,
                lab_id=lab_id,
                lab_version_id=lab_version_id,
                objective_key="obj_a",
                reason_code="RULE_A",
                trigger_event_index=31,
                occurred_at=replay_at,
            )
        ]
    )
    replay_result = process_pending_objective_completed_once(
        outbox_repo=replay_outbox,
        event_outbox_repo=_FakeCompletionEventOutbox(),
        template_reader=template_reader,
        objective_writer=objective_writer,
        completion_writer=completion_writer,
    )

    assert first_result.succeeded_count == 1
    assert replay_result.succeeded_count == 1
    assert completion_writer.current_status == "completed_success"
    assert completion_writer.current_reason_code == "ALL_REQUIRED_OBJECTIVES_COMPLETED"
    assert completion_writer.current_completed_at == occurred_at
    assert len(completion_writer.calls) == 2
    assert completion_writer.calls[0].applied is True
    assert completion_writer.calls[1].applied is False
    assert completion_writer.calls[1].decision_reason == "no_op_same_status"
