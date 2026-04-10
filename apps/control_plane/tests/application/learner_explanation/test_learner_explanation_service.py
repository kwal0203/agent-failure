from dataclasses import dataclass
from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

import pytest

from apps.control_plane.src.application.common.errors import (
    DuplicateIdempotencyKeyError,
)
from apps.control_plane.src.application.learner_explanation.errors import (
    InvalidLearnerExplanationError,
)
from apps.control_plane.src.application.learner_explanation.service import (
    inject_learner_explanation,
)
from apps.control_plane.src.application.learner_explanation.types import (
    LearnerExplanationInput,
    LearnerExplanationOutput,
)
from apps.control_plane.src.application.session_lifecycle.ports import Outbox
from apps.control_plane.src.application.trace.ports import TraceEventPort
from apps.control_plane.src.application.trace.types import TraceEvent


@dataclass
class _FakeRepo:
    existing: LearnerExplanationOutput | None = None
    created: LearnerExplanationOutput | None = None
    raise_on_inject: Exception | None = None
    get_calls: int = 0
    inject_calls: int = 0

    def get_by_session_and_idempotency_key(
        self, *, session_id: UUID, idempotency_key: str
    ) -> LearnerExplanationOutput | None:
        _ = (session_id, idempotency_key)
        self.get_calls += 1
        return self.existing

    def inject_learner_explanation(
        self, input: LearnerExplanationInput
    ) -> LearnerExplanationOutput:
        _ = input
        self.inject_calls += 1
        if self.raise_on_inject is not None:
            raise self.raise_on_inject
        if self.created is None:
            self.created = LearnerExplanationOutput(
                session_id=input.session_id,
                explanation_id=uuid4(),
                accepted=True,
            )
        return self.created


@dataclass
class _FakeTraceRepo(TraceEventPort):
    next_index: int = 0
    appended: list[TraceEvent] | None = None

    def append_trace_event(self, trace: TraceEvent) -> None:
        if self.appended is None:
            self.appended = []
        self.appended.append(trace)

    def list_trace_events_for_session(self, session_id: UUID) -> tuple[TraceEvent, ...]:
        _ = session_id
        return tuple(self.appended or [])

    def get_next_event_index(self, session_id: UUID) -> int:
        _ = session_id
        return self.next_index


@dataclass
class _FakeOutbox:
    enqueued: list[tuple[UUID, int, int, str]]

    def enqueue_for_evaluator(
        self,
        *,
        session_id: UUID,
        lab_id: UUID,
        lab_version_id: UUID,
        lab_difficulty: str,
        evaluator_version: int,
        start_event_index: int,
        end_event_index: int,
        requested_at: datetime | None = None,
    ) -> None:
        _ = (lab_id, lab_version_id, evaluator_version, requested_at)
        self.enqueued.append(
            (session_id, start_event_index, end_event_index, lab_difficulty)
        )


def _valid_input() -> LearnerExplanationInput:
    return LearnerExplanationInput(
        explanation="The model treated untrusted inbox content as authoritative instructions.",
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        lab_difficulty="medium",
        actor_user_id=uuid4(),
        idempotency_key="explain-service-key",
        source="learner",
    )


def test_inject_learner_explanation_happy_path_emits_trace_and_outbox() -> None:
    input_data = _valid_input()
    repo = _FakeRepo()
    trace_repo = _FakeTraceRepo(next_index=7, appended=[])
    outbox = _FakeOutbox(enqueued=[])

    result = inject_learner_explanation(
        repo=repo,
        learner_input=input_data,
        trace_repo=trace_repo,
        outbox=cast(Outbox, outbox),
    )

    assert result.accepted is True
    assert repo.inject_calls == 1
    assert trace_repo.appended is not None
    assert len(trace_repo.appended) == 1
    assert trace_repo.appended[0].event_type == "LEARNER_EXPLANATION_SUBMITTED"
    assert trace_repo.appended[0].event_index == 7
    assert len(outbox.enqueued) == 1
    assert outbox.enqueued[0] == (input_data.session_id, 7, 7, "medium")


def test_inject_learner_explanation_replay_returns_existing_without_side_effects() -> (
    None
):
    input_data = _valid_input()
    existing = LearnerExplanationOutput(
        session_id=input_data.session_id,
        explanation_id=uuid4(),
        accepted=True,
    )
    repo = _FakeRepo(existing=existing)
    trace_repo = _FakeTraceRepo(next_index=1, appended=[])
    outbox = _FakeOutbox(enqueued=[])

    result = inject_learner_explanation(
        repo=repo,
        learner_input=input_data,
        trace_repo=trace_repo,
        outbox=cast(Outbox, outbox),
    )

    assert result == existing
    assert repo.inject_calls == 0
    assert trace_repo.appended == []
    assert outbox.enqueued == []


def test_inject_learner_explanation_duplicate_race_replays_existing_without_side_effects() -> (
    None
):
    input_data = _valid_input()
    existing = LearnerExplanationOutput(
        session_id=input_data.session_id,
        explanation_id=uuid4(),
        accepted=True,
    )
    repo = _FakeRepo(
        existing=existing,
        raise_on_inject=DuplicateIdempotencyKeyError(code="DUPLICATE_IDEMPOTENCY_KEY"),
    )
    trace_repo = _FakeTraceRepo(next_index=2, appended=[])
    outbox = _FakeOutbox(enqueued=[])

    # First call to get_by -> None, so service attempts insert; second get_by (after
    # duplicate) replays existing.
    call_count = {"n": 0}

    def _get_by(
        *, session_id: UUID, idempotency_key: str
    ) -> LearnerExplanationOutput | None:
        _ = (session_id, idempotency_key)
        call_count["n"] += 1
        if call_count["n"] == 1:
            return None
        return existing

    repo.get_by_session_and_idempotency_key = _get_by  # type: ignore[method-assign]

    result = inject_learner_explanation(
        repo=repo,
        learner_input=input_data,
        trace_repo=trace_repo,
        outbox=cast(Outbox, outbox),
    )

    assert result == existing
    assert repo.inject_calls == 1
    assert trace_repo.appended == []
    assert outbox.enqueued == []


def test_inject_learner_explanation_rejects_blank_explanation() -> None:
    input_data = _valid_input()
    input_data = LearnerExplanationInput(
        explanation=" " * 30,
        session_id=input_data.session_id,
        lab_id=input_data.lab_id,
        lab_version_id=input_data.lab_version_id,
        lab_difficulty=input_data.lab_difficulty,
        actor_user_id=input_data.actor_user_id,
        idempotency_key=input_data.idempotency_key,
        source=input_data.source,
    )

    with pytest.raises(InvalidLearnerExplanationError) as exc:
        inject_learner_explanation(
            repo=_FakeRepo(),
            learner_input=input_data,
            trace_repo=_FakeTraceRepo(next_index=0, appended=[]),
            outbox=cast(Outbox, _FakeOutbox(enqueued=[])),
        )

    assert exc.value.code == "INVALID_EXPLANATION"
