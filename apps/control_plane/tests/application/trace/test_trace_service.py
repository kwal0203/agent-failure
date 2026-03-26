from dataclasses import dataclass
from datetime import datetime, timezone
from typing import cast
from uuid import UUID, uuid4

import pytest

from apps.control_plane.src.application.trace.errors import (
    MissingTraceContextError,
    UnknownTraceEventTypeError,
    UnknownTraceFamilyError,
)
from apps.control_plane.src.application.trace.ports import TraceEventPort
from apps.control_plane.src.application.trace.service import append_trace_event
from apps.control_plane.src.application.trace.types import TraceEvent, TraceFamily


@dataclass
class _FakeTraceRepo(TraceEventPort):
    appended: list[TraceEvent]

    def append_trace_event(self, trace: TraceEvent) -> None:
        self.appended.append(trace)

    def get_next_event_index(self, session_id: UUID) -> int:
        return 0


def _valid_lifecycle_trace() -> TraceEvent:
    return TraceEvent(
        event_id=uuid4(),
        session_id=uuid4(),
        family="lifecycle",
        event_type="SESSION_TRANSITIONED",
        occurred_at=datetime.now(timezone.utc),
        source="test",
        event_index=0,
        payload={"ok": True},
        trace_version=1,
    )


def test_append_trace_event_accepts_valid_lifecycle_event() -> None:
    repo = _FakeTraceRepo(appended=[])
    trace = _valid_lifecycle_trace()

    append_trace_event(trace=trace, repo=repo)

    assert repo.appended == [trace]


def test_append_trace_event_rejects_unknown_family() -> None:
    repo = _FakeTraceRepo(appended=[])
    trace = _valid_lifecycle_trace()
    # runtime bypass for negative-path validation test
    trace = TraceEvent(
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
        append_trace_event(trace=trace, repo=repo)


def test_append_trace_event_rejects_unknown_event_type() -> None:
    repo = _FakeTraceRepo(appended=[])
    trace = _valid_lifecycle_trace()
    trace = TraceEvent(
        event_id=trace.event_id,
        session_id=trace.session_id,
        family="lifecycle",
        event_type="NOT_ALLOWED",
        occurred_at=trace.occurred_at,
        source=trace.source,
        event_index=trace.event_index,
        payload=trace.payload,
        trace_version=trace.trace_version,
    )

    with pytest.raises(UnknownTraceEventTypeError):
        append_trace_event(trace=trace, repo=repo)


def test_append_trace_event_rejects_missing_learner_context() -> None:
    repo = _FakeTraceRepo(appended=[])
    trace = TraceEvent(
        event_id=uuid4(),
        session_id=uuid4(),
        family="learner",
        event_type="USER_PROMPT_SUBMITTED",
        occurred_at=datetime.now(timezone.utc),
        source="test",
        event_index=0,
        payload={"content": "hello"},
        trace_version=1,
        actor_user_id=None,
    )

    with pytest.raises(MissingTraceContextError):
        append_trace_event(trace=trace, repo=repo)
