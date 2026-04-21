from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from typing import cast
from uuid import UUID, uuid4

import pytest

from apps.control_plane.src.application.trace.errors import (
    MissingTraceContextError,
    TraceValidationError,
    UnknownTraceEventTypeError,
    UnknownTraceFamilyError,
)
from apps.control_plane.src.application.trace.ports import (
    TraceEventPort,
    TraceOutboxPort,
)
from apps.control_plane.src.application.trace.service import append_trace_event
from apps.control_plane.src.application.trace.types import TraceEvent, TraceFamily


@dataclass
class _FakeTraceRepo(TraceEventPort):
    appended: list[TraceEvent]

    def append_trace_event(self, trace: TraceEvent) -> None:
        self.appended.append(trace)

    def list_trace_events_for_session(self, session_id: UUID) -> tuple[TraceEvent, ...]:
        return tuple(t for t in self.appended if t.session_id == session_id)

    def get_next_event_index(self, session_id: UUID) -> int:
        _ = session_id
        return 0


@dataclass
class _FakeOutboxRepo(TraceOutboxPort):
    enqueued: list[tuple[UUID, UUID, UUID, str, int, int, int]]

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
        _ = requested_at
        self.enqueued.append(
            (
                session_id,
                lab_id,
                lab_version_id,
                lab_difficulty,
                evaluator_version,
                start_event_index,
                end_event_index,
            )
        )


def _event(
    *,
    family: TraceFamily,
    event_type: str,
    payload: dict[str, object],
    actor_user_id: UUID | None = None,
    event_index: int = 0,
    occurred_at: datetime | None = None,
) -> TraceEvent:
    return TraceEvent(
        event_id=uuid4(),
        session_id=uuid4(),
        family=family,
        event_type=event_type,
        occurred_at=occurred_at or datetime.now(UTC),
        source="schema-test",
        event_index=event_index,
        payload=payload,
        trace_version=1,
        actor_user_id=actor_user_id,
    )


@pytest.mark.parametrize(
    ("trace",),
    [
        (_event(family="lifecycle", event_type="SESSION_CREATED", payload={}),),
        (_event(family="lifecycle", event_type="SESSION_TRANSITIONED", payload={}),),
        (
            _event(
                family="learner",
                event_type="USER_PROMPT_SUBMITTED",
                payload={"content": "hello"},
                actor_user_id=uuid4(),
            ),
        ),
        (
            _event(
                family="runtime",
                event_type="RUNTIME_PROVISION_REQUESTED",
                payload={},
            ),
        ),
        (
            _event(
                family="runtime",
                event_type="RUNTIME_PROVISION_ACCEPTED",
                payload={},
            ),
        ),
        (
            _event(
                family="runtime",
                event_type="RUNTIME_PROVISION_FAILED",
                payload={"reason_code": "K8S_APPLY_FAILED"},
            ),
        ),
        (_event(family="runtime", event_type="RUNTIME_HEALTH_STATUS", payload={}),),
        (
            _event(
                family="tool",
                event_type="TOOL_CALL_REQUESTED",
                payload={"tool_name": "read_email"},
            ),
        ),
        (
            _event(
                family="tool",
                event_type="TOOL_CALL_SUCCEEDED",
                payload={"tool_name": "read_email"},
            ),
        ),
        (
            _event(
                family="tool",
                event_type="TOOL_CALL_FAILED",
                payload={"tool_name": "read_file", "error_code": "DENIED"},
            ),
        ),
        (_event(family="model", event_type="MODEL_TURN_STARTED", payload={}),),
        (_event(family="model", event_type="MODEL_CHUNK_EMITTED", payload={}),),
        (_event(family="model", event_type="MODEL_TURN_COMPLETED", payload={}),),
        (
            _event(
                family="model",
                event_type="MODEL_TURN_FAILED",
                payload={"provider": "openrouter", "error_code": "TIMEOUT"},
            ),
        ),
    ],
)
def test_trace_schema_accepts_supported_family_event_type_fixtures(
    trace: TraceEvent,
) -> None:
    repo = _FakeTraceRepo(appended=[])
    outbox_repo = _FakeOutboxRepo(enqueued=[])

    append_trace_event(trace=trace, repo=repo, outbox_repo=outbox_repo)

    assert repo.appended == [trace]


def test_trace_schema_rejects_unknown_family() -> None:
    repo = _FakeTraceRepo(appended=[])
    outbox_repo = _FakeOutboxRepo(enqueued=[])
    trace = _event(family="lifecycle", event_type="SESSION_CREATED", payload={})
    invalid_trace = TraceEvent(
        event_id=trace.event_id,
        session_id=trace.session_id,
        family=cast(TraceFamily, "unknown"),
        event_type=trace.event_type,
        occurred_at=trace.occurred_at,
        source=trace.source,
        event_index=trace.event_index,
        payload=trace.payload,
        trace_version=trace.trace_version,
    )

    with pytest.raises(UnknownTraceFamilyError):
        append_trace_event(trace=invalid_trace, repo=repo, outbox_repo=outbox_repo)


def test_trace_schema_rejects_unknown_event_type_for_known_family() -> None:
    repo = _FakeTraceRepo(appended=[])
    outbox_repo = _FakeOutboxRepo(enqueued=[])
    trace = _event(family="model", event_type="NOT_ALLOWED", payload={})

    with pytest.raises(UnknownTraceEventTypeError):
        append_trace_event(trace=trace, repo=repo, outbox_repo=outbox_repo)


def test_trace_schema_rejects_missing_learner_actor_context() -> None:
    repo = _FakeTraceRepo(appended=[])
    outbox_repo = _FakeOutboxRepo(enqueued=[])
    trace = _event(
        family="learner",
        event_type="USER_PROMPT_SUBMITTED",
        payload={"content": "hello"},
        actor_user_id=None,
    )

    with pytest.raises(MissingTraceContextError):
        append_trace_event(trace=trace, repo=repo, outbox_repo=outbox_repo)


def test_trace_schema_rejects_runtime_failed_missing_reason_code() -> None:
    repo = _FakeTraceRepo(appended=[])
    outbox_repo = _FakeOutboxRepo(enqueued=[])
    trace = _event(
        family="runtime",
        event_type="RUNTIME_PROVISION_FAILED",
        payload={"pod_name": "session-1234"},
    )

    with pytest.raises(MissingTraceContextError):
        append_trace_event(trace=trace, repo=repo, outbox_repo=outbox_repo)


def test_trace_schema_rejects_tool_failed_missing_required_payload_fields() -> None:
    repo = _FakeTraceRepo(appended=[])
    outbox_repo = _FakeOutboxRepo(enqueued=[])
    trace = _event(
        family="tool",
        event_type="TOOL_CALL_FAILED",
        payload={},
    )

    with pytest.raises(MissingTraceContextError):
        append_trace_event(trace=trace, repo=repo, outbox_repo=outbox_repo)


def test_trace_schema_rejects_model_failed_missing_required_payload_fields() -> None:
    repo = _FakeTraceRepo(appended=[])
    outbox_repo = _FakeOutboxRepo(enqueued=[])
    trace = _event(
        family="model",
        event_type="MODEL_TURN_FAILED",
        payload={"provider": "openrouter"},
    )

    with pytest.raises(MissingTraceContextError):
        append_trace_event(trace=trace, repo=repo, outbox_repo=outbox_repo)


def test_trace_schema_rejects_negative_event_index() -> None:
    repo = _FakeTraceRepo(appended=[])
    outbox_repo = _FakeOutboxRepo(enqueued=[])
    trace = _event(
        family="lifecycle",
        event_type="SESSION_CREATED",
        payload={},
        event_index=-1,
    )

    with pytest.raises(TraceValidationError):
        append_trace_event(trace=trace, repo=repo, outbox_repo=outbox_repo)


def test_trace_schema_rejects_naive_occurred_at() -> None:
    repo = _FakeTraceRepo(appended=[])
    outbox_repo = _FakeOutboxRepo(enqueued=[])
    trace = _event(
        family="lifecycle",
        event_type="SESSION_CREATED",
        payload={},
        occurred_at=datetime.now(),
    )

    with pytest.raises(TraceValidationError):
        append_trace_event(trace=trace, repo=repo, outbox_repo=outbox_repo)


def test_trace_schema_rejects_non_utc_occurred_at() -> None:
    repo = _FakeTraceRepo(appended=[])
    outbox_repo = _FakeOutboxRepo(enqueued=[])
    trace = _event(
        family="lifecycle",
        event_type="SESSION_CREATED",
        payload={},
        occurred_at=datetime.now(timezone(timedelta(hours=-7))),
    )

    with pytest.raises(TraceValidationError):
        append_trace_event(trace=trace, repo=repo, outbox_repo=outbox_repo)
