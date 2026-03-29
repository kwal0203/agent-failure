from datetime import datetime, timezone
from typing import cast
from uuid import uuid4

import pytest

from apps.control_plane.src.application.common.errors import ForbiddenError
from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.evaluator_feedback.service import (
    get_session_evaluator_feedback,
)
from apps.control_plane.src.application.evaluator_feedback.types import (
    EvaluatorPersistedResult,
    ResultType,
)


class _FakeRepo:
    def __init__(self, results: list[EvaluatorPersistedResult]) -> None:
        self._results = results

    def list_results_for_session(self, session_id) -> list[EvaluatorPersistedResult]:
        _ = session_id
        return list(self._results)


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
