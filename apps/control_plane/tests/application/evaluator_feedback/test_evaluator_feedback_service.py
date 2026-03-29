from datetime import datetime, timezone
import asyncio
from typing import cast
from uuid import UUID, uuid4

import pytest

from apps.control_plane.src.application.common.errors import ForbiddenError
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.evaluator_feedback.service import (
    get_session_evaluator_feedback,
    process_pending_feedback_publish_once,
)
from apps.control_plane.src.application.evaluator_feedback.types import (
    EvaluatorPersistedResult,
    LearnerEvaluatorFeedback,
    LearnerFeedbackPublishResult,
    PendingLearnerFeedbackPublishEvent,
    ResultType,
)


class _FakeRepo:
    def __init__(self, results: list[EvaluatorPersistedResult]) -> None:
        self._results = results

    def list_results_for_session(
        self, session_id: UUID
    ) -> tuple[EvaluatorPersistedResult, ...]:
        _ = session_id
        return tuple(self._results)


class _FakeEvalRepoBySession:
    def __init__(self, by_session: dict[UUID, list[EvaluatorPersistedResult]]) -> None:
        self._by_session = by_session

    def list_results_for_session(
        self, session_id: UUID
    ) -> tuple[EvaluatorPersistedResult, ...]:
        return tuple(self._by_session.get(session_id, []))


class _FakeOutboxRepo:
    def __init__(self, events: list[PendingLearnerFeedbackPublishEvent]) -> None:
        self._events = events
        self.processed: list[UUID] = []
        self.retryable_failed: list[tuple[UUID, str]] = []
        self.terminal_failed: list[tuple[UUID, str]] = []

    def claim_pending_feedback_publish(
        self, *, limit: int = 20, now: datetime | None = None
    ) -> list[PendingLearnerFeedbackPublishEvent]:
        _ = (limit, now)
        return list(self._events)

    def mark_processed(
        self, *, outbox_event_id: UUID, processed_at: datetime | None = None
    ) -> None:
        _ = processed_at
        self.processed.append(outbox_event_id)

    def mark_retryable_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        backoff_seconds: int = 15,
        failed_at: datetime | None = None,
    ) -> None:
        _ = (backoff_seconds, failed_at)
        self.retryable_failed.append((outbox_event_id, error_message))

    def mark_terminal_failure(
        self,
        *,
        outbox_event_id: UUID,
        error_message: str,
        failed_at: datetime | None = None,
    ) -> None:
        _ = failed_at
        self.terminal_failed.append((outbox_event_id, error_message))


class _FakePublisher:
    def __init__(self, *, raises: Exception | None = None) -> None:
        self._raises = raises
        self.calls: list[tuple[UUID, tuple[LearnerEvaluatorFeedback, ...]]] = []

    async def publish_session_feedback(
        self, session_id: UUID, feedback: tuple[LearnerEvaluatorFeedback, ...]
    ) -> None:
        self.calls.append((session_id, feedback))
        if self._raises is not None:
            raise self._raises


def _make_result(
    *,
    result_type: ResultType,
    code: str,
    reason_code: str = "REASON",
    feedback_payload: dict[str, object] | None = None,
) -> EvaluatorPersistedResult:
    return EvaluatorPersistedResult(
        id=uuid4(),
        idempotency_key=f"idempo:{uuid4()}",
        result_type=result_type,
        code=code,
        trigger_event_index=1,
        trigger_start_event_index=None,
        trigger_end_event_index=None,
        feedback_level="flag",
        reason_code=reason_code,
        feedback_payload=feedback_payload or {},
        created_at=datetime.now(timezone.utc),
        session_id=uuid4(),
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        evaluator_version=1,
    )


@pytest.mark.parametrize(
    ("result_type", "expected_status"),
    [
        ("constraint_violation", "learned"),
        ("success_signal", "learned"),
        ("partial_success", "progress"),
        ("no_effect", "no_progress"),
        ("terminal_outcome", "session_terminal"),
    ],
)
def test_get_session_evaluator_feedback_maps_status(
    result_type: ResultType, expected_status: str
) -> None:
    repo = _FakeRepo(
        results=[
            _make_result(
                result_type=result_type,
                code="pi.attack_attempt_blocked",
            )
        ]
    )
    principal = PrincipalContext(user_id=uuid4(), role="learner")

    feedback = get_session_evaluator_feedback(
        principal=principal, session_id=uuid4(), repo=repo
    )

    assert len(feedback) == 1
    assert feedback[0].status == expected_status


def test_get_session_evaluator_feedback_derives_snippets_by_code() -> None:
    repo = _FakeRepo(
        results=[
            _make_result(
                result_type="constraint_violation",
                code="pi.secret_exfiltration_success",
                feedback_payload={"matched_value": "FLAG{test-secret}"},
            ),
            _make_result(
                result_type="constraint_violation",
                code="pi.protected_tool_access_violation",
                feedback_payload={
                    "tool_name": "fs.read",
                    "target_resource": "/protected/flag.txt",
                },
            ),
            _make_result(
                result_type="partial_success",
                code="pi.attack_attempt_blocked",
                feedback_payload={
                    "blocked_by": "model_policy",
                    "block_reason_code": "POLICY_DENIED",
                },
            ),
        ]
    )
    principal = PrincipalContext(user_id=uuid4(), role="learner")

    feedback = get_session_evaluator_feedback(
        principal=principal, session_id=uuid4(), repo=repo
    )

    assert feedback[0].evidence_snippet == "FLAG{test-secret}"
    assert (
        feedback[1].evidence_snippet
        == "fs.read accessed protected resource /protected/flag.txt."
    )
    assert (
        feedback[2].evidence_snippet
        == "Attack attempt blocked by model_policy (POLICY_DENIED)"
    )


def test_get_session_evaluator_feedback_raises_on_unknown_result_type() -> None:
    repo = _FakeRepo(
        results=[
            _make_result(
                result_type=cast(ResultType, "unknown_type"),
                code="pi.attack_attempt_blocked",
            )
        ]
    )
    principal = PrincipalContext(user_id=uuid4(), role="learner")

    with pytest.raises(ValueError, match="Unsupported result_type: unknown_type"):
        get_session_evaluator_feedback(
            principal=principal, session_id=uuid4(), repo=repo
        )


def test_get_session_evaluator_feedback_rejects_forbidden_role() -> None:
    repo = _FakeRepo(results=[])
    principal = PrincipalContext(user_id=uuid4(), role="viewer")

    with pytest.raises(ForbiddenError):
        get_session_evaluator_feedback(
            principal=principal, session_id=uuid4(), repo=repo
        )


def test_process_pending_feedback_publish_once_success_path() -> None:
    session_id = uuid4()
    outbox_event_id = uuid4()
    outbox = _FakeOutboxRepo(
        events=[
            PendingLearnerFeedbackPublishEvent(
                outbox_event_id=outbox_event_id,
                session_id=session_id,
                attempt_count=0,
                requested_at=None,
            )
        ]
    )
    eval_repo = _FakeEvalRepoBySession(
        by_session={
            session_id: [
                _make_result(
                    result_type="constraint_violation",
                    code="pi.secret_exfiltration_success",
                    feedback_payload={"matched_value": "FLAG{abc}"},
                )
            ]
        }
    )
    publisher = _FakePublisher()

    result = asyncio.run(
        process_pending_feedback_publish_once(
            outbox_repo=outbox, eval_repo=eval_repo, publisher=publisher
        )
    )

    assert result == LearnerFeedbackPublishResult(
        claimed_count=1, succeeded_count=1, failed_count=0, retried_count=0
    )
    assert outbox.processed == [outbox_event_id]
    assert outbox.retryable_failed == []
    assert outbox.terminal_failed == []
    assert len(publisher.calls) == 1
    assert publisher.calls[0][0] == session_id
    assert publisher.calls[0][1][0].status == "learned"


def test_process_pending_feedback_publish_once_marks_terminal_on_unknown_result_type() -> (
    None
):
    session_id = uuid4()
    outbox_event_id = uuid4()
    outbox = _FakeOutboxRepo(
        events=[
            PendingLearnerFeedbackPublishEvent(
                outbox_event_id=outbox_event_id,
                session_id=session_id,
                attempt_count=0,
                requested_at=None,
            )
        ]
    )
    eval_repo = _FakeEvalRepoBySession(
        by_session={
            session_id: [
                _make_result(
                    result_type=cast(ResultType, "unknown_type"),
                    code="pi.attack_attempt_blocked",
                )
            ]
        }
    )
    publisher = _FakePublisher()

    result = asyncio.run(
        process_pending_feedback_publish_once(
            outbox_repo=outbox, eval_repo=eval_repo, publisher=publisher
        )
    )

    assert result == LearnerFeedbackPublishResult(
        claimed_count=1, succeeded_count=0, failed_count=1, retried_count=0
    )
    assert outbox.processed == []
    assert outbox.retryable_failed == []
    assert len(outbox.terminal_failed) == 1
    assert outbox.terminal_failed[0][0] == outbox_event_id
    assert publisher.calls == []


def test_process_pending_feedback_publish_once_marks_retryable_on_publisher_error() -> (
    None
):
    session_id = uuid4()
    outbox_event_id = uuid4()
    outbox = _FakeOutboxRepo(
        events=[
            PendingLearnerFeedbackPublishEvent(
                outbox_event_id=outbox_event_id,
                session_id=session_id,
                attempt_count=0,
                requested_at=None,
            )
        ]
    )
    eval_repo = _FakeEvalRepoBySession(
        by_session={
            session_id: [
                _make_result(
                    result_type="constraint_violation",
                    code="pi.secret_exfiltration_success",
                    feedback_payload={"matched_value": "FLAG{abc}"},
                )
            ]
        }
    )
    publisher = _FakePublisher(raises=RuntimeError("publish failed"))

    result = asyncio.run(
        process_pending_feedback_publish_once(
            outbox_repo=outbox, eval_repo=eval_repo, publisher=publisher
        )
    )

    assert result == LearnerFeedbackPublishResult(
        claimed_count=1, succeeded_count=0, failed_count=0, retried_count=1
    )
    assert outbox.processed == []
    assert outbox.terminal_failed == []
    assert len(outbox.retryable_failed) == 1
    assert outbox.retryable_failed[0][0] == outbox_event_id
    assert len(publisher.calls) == 1
