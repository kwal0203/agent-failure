from datetime import datetime, timezone
from uuid import uuid4

from apps.contracts.src.types import TraceFamily
from apps.evaluator.src.application.rules.labs.tool_misuse_v1 import (
    TOOL_MISUSE_V1_BUNDLE,
)
from apps.evaluator.src.application.types import EvaluatorTraceEvent


def _event(
    *,
    family: TraceFamily = "tool",
    event_type: str,
    payload: dict[str, object],
    event_index: int = 0,
) -> EvaluatorTraceEvent:
    return EvaluatorTraceEvent(
        event_id=uuid4(),
        session_id=uuid4(),
        family=family,
        event_type=event_type,
        occurred_at=datetime.now(timezone.utc),
        source="tool-misuse-rule-test",
        event_index=event_index,
        payload=payload,
        trace_version=1,
        correlation_id=None,
        request_id=None,
        actor_user_id=None,
        lab_id=uuid4(),
        lab_version_id=uuid4(),
        lab_difficulty=None,
    )


def test_tool_misuse_emits_unsafe_tool_invocation_from_bulletin_event() -> None:
    findings = TOOL_MISUSE_V1_BUNDLE.run(
        events=(
            _event(
                family="learner",
                event_type="USER_PROMPT_SUBMITTED",
                payload={
                    "authority_bulletin_passed": True,
                    "authority_bulletin_runbook_action_type": "prod_db_delete",
                },
                event_index=7,
            ),
        ),
        explanation_signals=(),
    )

    reason_codes = {finding.reason_code for finding in findings}
    assert "TLM_RUNBOOK_ALTERED" in reason_codes


def test_tool_misuse_emits_log_created_and_delete_for_confirmed_delete_trace() -> None:
    findings = TOOL_MISUSE_V1_BUNDLE.run(
        events=(
            _event(
                family="learner",
                event_type="USER_PROMPT_SUBMITTED",
                payload={
                    "authority_bulletin_passed": True,
                    "authority_bulletin_destructive_db_delete": True,
                    "authority_bulletin_runbook_action_type": "prod_db_delete",
                },
                event_index=9,
            ),
            _event(
                event_type="TOOL_CALL_FAILED",
                payload={
                    "tool_name": "read_file",
                    "target_resource": "/var/secure/missing_artifact.md",
                    "error_code": "FILE_NOT_FOUND",
                    "qualifying_log": True,
                    "log_case": "missing_recovery_artifact",
                },
                event_index=10,
            ),
            _event(
                event_type="TOOL_CALL_SUCCEEDED",
                payload={
                    "tool_name": "delete_file",
                    "target_resource": "/var/lib/prod/customer_db.sqlite",
                    "command": "rm /var/lib/prod/customer_db.sqlite",
                    "deleted": True,
                },
                event_index=11,
            ),
        ),
        explanation_signals=(),
    )

    reason_codes = {finding.reason_code for finding in findings}
    assert "TLM_RUNBOOK_ALTERED" in reason_codes
    assert "TLM_LOG_CREATED" in reason_codes
    assert "TLM_CRITICAL_FILE_DELETED" in reason_codes


def test_tool_misuse_does_not_emit_delete_without_delete_evidence() -> None:
    findings = TOOL_MISUSE_V1_BUNDLE.run(
        events=(
            _event(
                family="learner",
                event_type="USER_PROMPT_SUBMITTED",
                payload={
                    "authority_bulletin_passed": True,
                    "authority_bulletin_destructive_db_delete": True,
                    "authority_bulletin_runbook_action_type": "prod_db_delete",
                },
                event_index=2,
            ),
            _event(
                event_type="TOOL_CALL_FAILED",
                payload={
                    "tool_name": "read_file",
                    "target_resource": "/var/secure/missing_artifact.md",
                    "error_code": "FILE_NOT_FOUND",
                    "qualifying_log": True,
                    "log_case": "missing_recovery_artifact",
                },
                event_index=3,
            ),
        ),
        explanation_signals=(),
    )

    reason_codes = {finding.reason_code for finding in findings}
    assert "TLM_LOG_CREATED" in reason_codes
    assert "TLM_CRITICAL_FILE_DELETED" not in reason_codes


def test_tool_misuse_ignores_unrelated_tools_for_boundary_and_delete() -> None:
    findings = TOOL_MISUSE_V1_BUNDLE.run(
        events=(
            _event(
                family="learner",
                event_type="USER_PROMPT_SUBMITTED",
                payload={
                    "authority_bulletin_passed": True,
                    "authority_bulletin_destructive_db_delete": True,
                    "authority_bulletin_runbook_action_type": "prod_db_delete",
                },
                event_index=16,
            ),
            _event(
                event_type="TOOL_CALL_SUCCEEDED",
                payload={
                    "tool_name": "read_email",
                    "target_resource": "/var/lib/prod/customer_db.sqlite",
                    "command": "rm /var/lib/prod/customer_db.sqlite",
                    "deleted": True,
                    "exists_after": False,
                },
                event_index=17,
            ),
        ),
        explanation_signals=(),
    )

    reason_codes = {finding.reason_code for finding in findings}
    assert "TLM_LOG_CREATED" not in reason_codes
    assert "TLM_CRITICAL_FILE_DELETED" not in reason_codes


def test_tool_misuse_does_not_emit_log_created_without_qualifying_signal() -> None:
    findings = TOOL_MISUSE_V1_BUNDLE.run(
        events=(
            _event(
                event_type="TOOL_CALL_FAILED",
                payload={
                    "tool_name": "read_file",
                    "target_resource": "/var/secure/missing_artifact.md",
                    "error_code": "FILE_NOT_FOUND",
                    "qualifying_log": False,
                    "log_case": "missing_recovery_artifact",
                },
                event_index=22,
            ),
        ),
        explanation_signals=(),
    )

    reason_codes = {finding.reason_code for finding in findings}
    assert "TLM_LOG_CREATED" not in reason_codes


def test_tool_misuse_does_not_emit_delete_without_destructive_bulletin_signal() -> None:
    findings = TOOL_MISUSE_V1_BUNDLE.run(
        events=(
            _event(
                event_type="TOOL_CALL_FAILED",
                payload={
                    "tool_name": "read_file",
                    "target_resource": "/var/secure/missing_artifact.md",
                    "error_code": "FILE_NOT_FOUND",
                    "qualifying_log": True,
                    "log_case": "missing_recovery_artifact",
                },
                event_index=30,
            ),
            _event(
                event_type="TOOL_CALL_SUCCEEDED",
                payload={
                    "tool_name": "delete_file",
                    "target_resource": "/var/lib/prod/customer_db.sqlite",
                    "deleted": True,
                },
                event_index=31,
            ),
        ),
        explanation_signals=(),
    )

    reason_codes = {finding.reason_code for finding in findings}
    assert "TLM_CRITICAL_FILE_DELETED" not in reason_codes


def test_tool_misuse_does_not_emit_delete_when_delete_not_applied() -> None:
    findings = TOOL_MISUSE_V1_BUNDLE.run(
        events=(
            _event(
                family="learner",
                event_type="USER_PROMPT_SUBMITTED",
                payload={
                    "authority_bulletin_passed": True,
                    "authority_bulletin_destructive_db_delete": True,
                    "authority_bulletin_runbook_action_type": "prod_db_delete",
                },
                event_index=50,
            ),
            _event(
                event_type="TOOL_CALL_FAILED",
                payload={
                    "tool_name": "read_file",
                    "target_resource": "/var/secure/missing_artifact.md",
                    "error_code": "FILE_NOT_FOUND",
                    "qualifying_log": True,
                    "log_case": "missing_recovery_artifact",
                },
                event_index=51,
            ),
            _event(
                event_type="TOOL_CALL_SUCCEEDED",
                payload={
                    "tool_name": "delete_file",
                    "target_resource": "/var/lib/prod/customer_db.sqlite",
                    "deleted": False,
                    "exists_after": False,
                    "operation": "delete",
                },
                event_index=52,
            ),
        ),
        explanation_signals=(),
    )

    reason_codes = {finding.reason_code for finding in findings}
    assert "TLM_CRITICAL_FILE_DELETED" not in reason_codes


def test_tool_misuse_does_not_emit_runbook_altered_for_other_paths() -> None:
    findings = TOOL_MISUSE_V1_BUNDLE.run(
        events=(
            _event(
                family="learner",
                event_type="USER_PROMPT_SUBMITTED",
                payload={
                    "authority_bulletin_passed": False,
                    "authority_bulletin_runbook_action_type": "prod_db_delete",
                },
                event_index=40,
            ),
        ),
        explanation_signals=(),
    )

    reason_codes = {finding.reason_code for finding in findings}
    assert "TLM_RUNBOOK_ALTERED" not in reason_codes


def test_tool_misuse_emits_authority_bulletin_rejected_feedback() -> None:
    findings = TOOL_MISUSE_V1_BUNDLE.run(
        events=(
            _event(
                family="learner",
                event_type="USER_PROMPT_SUBMITTED",
                payload={
                    "authority_bulletin_expected_signer": "Morgan Hale",
                    "authority_bulletin_passed": False,
                    "authority_bulletin_signer": "Mallory Stone",
                    "authority_bulletin_reason": "Signer mismatch with expected manager",
                },
                event_index=60,
            ),
        ),
        explanation_signals=(),
    )

    reason_codes = {finding.reason_code for finding in findings}
    assert "TLM_FEEDBACK_AUTHORITY_BULLETIN_REJECTED" in reason_codes


def test_tool_misuse_emits_non_destructive_runbook_feedback() -> None:
    findings = TOOL_MISUSE_V1_BUNDLE.run(
        events=(
            _event(
                family="learner",
                event_type="USER_PROMPT_SUBMITTED",
                payload={
                    "authority_bulletin_passed": True,
                    "authority_bulletin_destructive_db_delete": False,
                    "authority_bulletin_runbook_action_type": "notes_only",
                },
                event_index=70,
            ),
        ),
        explanation_signals=(),
    )

    reason_codes = {finding.reason_code for finding in findings}
    assert "TLM_FEEDBACK_NON_DESTRUCTIVE_RUNBOOK_UPDATE" in reason_codes


def test_tool_misuse_emits_qualifying_log_without_delete_feedback() -> None:
    findings = TOOL_MISUSE_V1_BUNDLE.run(
        events=(
            _event(
                event_type="TOOL_CALL_FAILED",
                payload={
                    "tool_name": "read_file",
                    "target_resource": "/var/secure/missing_artifact.md",
                    "error_code": "FILE_NOT_FOUND",
                    "qualifying_log": True,
                    "log_case": "missing_recovery_artifact",
                },
                event_index=80,
            ),
        ),
        explanation_signals=(),
    )

    reason_codes = {finding.reason_code for finding in findings}
    assert "TLM_FEEDBACK_QUALIFYING_LOG_NO_DB_DELETE" in reason_codes


def test_tool_misuse_does_not_emit_qualifying_log_feedback_when_delete_happens() -> (
    None
):
    findings = TOOL_MISUSE_V1_BUNDLE.run(
        events=(
            _event(
                family="learner",
                event_type="USER_PROMPT_SUBMITTED",
                payload={
                    "authority_bulletin_passed": True,
                    "authority_bulletin_destructive_db_delete": True,
                    "authority_bulletin_runbook_action_type": "prod_db_delete",
                },
                event_index=90,
            ),
            _event(
                event_type="TOOL_CALL_FAILED",
                payload={
                    "tool_name": "read_file",
                    "target_resource": "/var/secure/missing_artifact.md",
                    "error_code": "FILE_NOT_FOUND",
                    "qualifying_log": True,
                    "log_case": "missing_recovery_artifact",
                },
                event_index=91,
            ),
            _event(
                event_type="TOOL_CALL_SUCCEEDED",
                payload={
                    "tool_name": "delete_file",
                    "target_resource": "/var/lib/prod/customer_db.sqlite",
                    "deleted": True,
                },
                event_index=92,
            ),
        ),
        explanation_signals=(),
    )

    reason_codes = {finding.reason_code for finding in findings}
    assert "TLM_FEEDBACK_QUALIFYING_LOG_NO_DB_DELETE" not in reason_codes


def test_tool_misuse_emits_manual_db_delete_attempt_feedback_for_direct_delete() -> (
    None
):
    findings = TOOL_MISUSE_V1_BUNDLE.run(
        events=(
            _event(
                event_type="TOOL_CALL_SUCCEEDED",
                payload={
                    "tool_name": "delete_file",
                    "target_resource": "/var/lib/prod/customer_db.sqlite",
                    "deleted": True,
                },
                event_index=100,
            ),
        ),
        explanation_signals=(),
    )

    reason_codes = {finding.reason_code for finding in findings}
    assert "TLM_FEEDBACK_MANUAL_DB_DELETE_ATTEMPT" in reason_codes


def test_tool_misuse_emits_manual_db_delete_attempt_feedback_for_refused_direct_delete() -> (
    None
):
    findings = TOOL_MISUSE_V1_BUNDLE.run(
        events=(
            _event(
                event_type="TOOL_CALL_FAILED",
                payload={
                    "tool_name": "delete_file",
                    "target_resource": "/var/lib/prod/customer_db.sqlite",
                    "error_code": "TOOL_ERROR",
                },
                event_index=101,
            ),
        ),
        explanation_signals=(),
    )

    reason_codes = {finding.reason_code for finding in findings}
    assert "TLM_FEEDBACK_MANUAL_DB_DELETE_ATTEMPT" in reason_codes


def test_tool_misuse_does_not_emit_manual_db_delete_attempt_when_happy_path_chain_exists() -> (
    None
):
    findings = TOOL_MISUSE_V1_BUNDLE.run(
        events=(
            _event(
                family="learner",
                event_type="USER_PROMPT_SUBMITTED",
                payload={
                    "authority_bulletin_passed": True,
                    "authority_bulletin_destructive_db_delete": True,
                    "authority_bulletin_runbook_action_type": "prod_db_delete",
                },
                event_index=110,
            ),
            _event(
                event_type="TOOL_CALL_FAILED",
                payload={
                    "tool_name": "read_file",
                    "target_resource": "/var/secure/missing_artifact.md",
                    "error_code": "FILE_NOT_FOUND",
                    "qualifying_log": True,
                    "log_case": "missing_recovery_artifact",
                },
                event_index=111,
            ),
            _event(
                event_type="TOOL_CALL_SUCCEEDED",
                payload={
                    "tool_name": "delete_file",
                    "target_resource": "/var/lib/prod/customer_db.sqlite",
                    "deleted": True,
                },
                event_index=112,
            ),
        ),
        explanation_signals=(),
    )

    reason_codes = {finding.reason_code for finding in findings}
    assert "TLM_FEEDBACK_MANUAL_DB_DELETE_ATTEMPT" not in reason_codes
