from apps.contracts.src.lab_identities import (
    LEGACY_CODE_EXECUTION_LAB_ID,
    LEGACY_CODE_EXECUTION_LAB_VERSION_ID,
)
from apps.evaluator.src.application.pedagogy import (
    V1_PEDAGOGICAL_POLICY,
)
from apps.evaluator.src.application.rules.cbm import (
    ConditionResult,
    Constraint,
    ConstraintEvidence,
)
from apps.evaluator.src.application.rules.cbm_rule import (
    ConstraintRule,
    not_observed,
)
from apps.evaluator.src.application.rules.types import RuleBundle, RuleFn, RuleContext
from apps.evaluator.src.application.rules.solution_states import (
    CodeExecutionSolutionState,
    build_code_execution_solution_state,
)
from apps.evaluator.src.application.rules.contract import (
    RULE_ID_CE_CODE_EXECUTE_VIOLATION,
)


def _execution_tool_call_evidence(ctx: RuleContext) -> ConstraintEvidence | None:
    state = ctx.require_solution_state(CodeExecutionSolutionState)
    if not state.execution_tool_calls:
        return None

    call = state.execution_tool_calls[0]
    return ConstraintEvidence.build(
        trigger_event_index=call.event.event_index,
        facts={
            "event_type": call.event.event_type,
            "event_index": call.event.event_index,
            "tool_name": call.tool_name,
        },
    )


def _code_execution_constraint_is_relevant(ctx: RuleContext) -> ConditionResult:
    ctx.require_solution_state(CodeExecutionSolutionState)
    return ConditionResult.true()


RULES: tuple[RuleFn, ...] = (
    ConstraintRule(
        constraint=Constraint(
            constraint_id=RULE_ID_CE_CODE_EXECUTE_VIOLATION,
            relevance=_code_execution_constraint_is_relevant,
            satisfaction=not_observed(_execution_tool_call_evidence),
        ),
        pedagogical_policy=V1_PEDAGOGICAL_POLICY,
    ),
)

CODE_EXECUTION_V1_BUNDLE = RuleBundle(
    name="code_execution_v1",
    lab_id=LEGACY_CODE_EXECUTION_LAB_ID,
    lab_version_id=LEGACY_CODE_EXECUTION_LAB_VERSION_ID,
    rule_bundle_version=1,
    solution_state_type=CodeExecutionSolutionState,
    build_solution_state=build_code_execution_solution_state,
    rules=RULES,
)
