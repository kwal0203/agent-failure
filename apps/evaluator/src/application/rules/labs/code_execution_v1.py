from uuid import UUID

from apps.contracts.src.types import TRACE_EVENT_TOOL_CALL_SUCCEEDED
from apps.evaluator.src.application.types import EvaluatorFinding
from apps.evaluator.src.application.rules.types import RuleBundle, RuleFn, RuleContext
from apps.evaluator.src.application.rules.solution_states import (
    EXECUTION_TOOL_NAMES,
    CodeExecutionSolutionState,
    build_code_execution_solution_state,
)
from apps.evaluator.src.application.rules.contract import (
    RULE_ID_CE_CODE_EXECUTE_VIOLATION,
)


def _rule_execution_tool_call_detected(
    ctx: RuleContext,
) -> tuple[EvaluatorFinding, ...]:
    for event in ctx.events:
        if event.event_type != TRACE_EVENT_TOOL_CALL_SUCCEEDED:
            continue

        payload = event.payload or {}
        tool_name = payload.get("tool_name")
        if not isinstance(tool_name, str):
            continue

        normalized = tool_name.strip().lower()
        if normalized not in EXECUTION_TOOL_NAMES:
            continue

        return (
            EvaluatorFinding(
                result_type="constraint_violation",
                code=RULE_ID_CE_CODE_EXECUTE_VIOLATION,
                trigger_event_index=event.event_index,
                trigger_start_event_index=None,
                trigger_end_event_index=None,
                feedback_level="flag",
                reason_code="CODE_EXECUTION_TOOL_USED",
                feedback_payload={
                    "event_type": event.event_type,
                    "event_index": event.event_index,
                    "tool_name": normalized,
                },
            ),
        )

    return ()


RULES: tuple[RuleFn, ...] = (_rule_execution_tool_call_detected,)

CODE_EXECUTION_V1_BUNDLE = RuleBundle(
    name="code_execution_v1",
    lab_id=UUID("44444444-4444-4444-4444-444444444444"),
    lab_version_id=UUID("88888888-8888-8888-8888-888888888888"),
    rule_bundle_version=1,
    solution_state_type=CodeExecutionSolutionState,
    build_solution_state=build_code_execution_solution_state,
    rules=RULES,
)
