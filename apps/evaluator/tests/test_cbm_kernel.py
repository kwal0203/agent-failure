from dataclasses import dataclass

import pytest

from apps.evaluator.src.application.rules.cbm import (
    ConditionResult,
    Constraint,
    ConstraintEvaluation,
    ConstraintEvidence,
)
from apps.evaluator.src.application.rules.cbm_compat import (
    CompatibleConstraintRule,
    LegacyFindingMapping,
    LegacyFindingSpec,
    map_evaluation_to_finding,
)
from apps.evaluator.src.application.rules.solution_states import LabSolutionState
from apps.evaluator.src.application.rules.trace_index import TraceIndex
from apps.evaluator.src.application.rules.types import RuleContext, RuleFn


@dataclass(frozen=True)
class ExampleState:
    attempted: bool
    safe: bool


def _constraint() -> Constraint[ExampleState]:
    return Constraint(
        constraint_id="SAFE_ACTION_REQUIRED",
        relevance=lambda state: ConditionResult(holds=state.attempted),
        satisfaction=lambda state: ConditionResult(
            holds=state.safe,
            evidence=ConstraintEvidence.build(
                trigger_event_index=7,
                trigger_start_event_index=6,
                trigger_end_event_index=7,
                facts={"action": "delete", "safe": state.safe},
            ),
        ),
    )


def test_irrelevant_constraint_does_not_evaluate_satisfaction() -> None:
    satisfaction_called = False

    def satisfaction(_state: ExampleState) -> ConditionResult:
        nonlocal satisfaction_called
        satisfaction_called = True
        return ConditionResult.true()

    constraint = Constraint(
        constraint_id="ONLY_WHEN_ATTEMPTED",
        relevance=lambda state: ConditionResult(holds=state.attempted),
        satisfaction=satisfaction,
    )

    result = constraint.evaluate(ExampleState(attempted=False, safe=False))

    assert result.status == "not_relevant"
    assert result.satisfaction is None
    assert satisfaction_called is False


@pytest.mark.parametrize(
    ("safe", "expected_status"),
    [(True, "satisfied"), (False, "violated")],
)
def test_relevant_constraint_reports_satisfaction_explicitly(
    safe: bool, expected_status: str
) -> None:
    result = _constraint().evaluate(ExampleState(attempted=True, safe=safe))

    assert result.status == expected_status
    assert result.relevance.holds is True
    assert result.satisfaction is not None
    assert result.satisfaction.holds is safe


def test_constraint_evaluation_rejects_inconsistent_states() -> None:
    with pytest.raises(ValueError, match="relevant constraint requires"):
        ConstraintEvaluation(
            constraint_id="BROKEN",
            relevance=ConditionResult.true(),
            satisfaction=None,
        )

    with pytest.raises(ValueError, match="irrelevant constraint must not"):
        ConstraintEvaluation(
            constraint_id="BROKEN",
            relevance=ConditionResult.false(),
            satisfaction=ConditionResult.true(),
        )


def test_legacy_mapping_projects_violation_without_leaking_policy_into_kernel() -> None:
    result = _constraint().evaluate(ExampleState(attempted=True, safe=False))
    mapping = LegacyFindingMapping(
        violated=LegacyFindingSpec(
            result_type="constraint_violation",
            feedback_level="flag",
            reason_code="UNSAFE_ACTION",
            feedback_payload={"source": "cbm"},
        )
    )

    finding = map_evaluation_to_finding(result, mapping)

    assert finding is not None
    assert finding.result_type == "constraint_violation"
    assert finding.code == "SAFE_ACTION_REQUIRED"
    assert finding.trigger_event_index == 7
    assert finding.trigger_start_event_index == 6
    assert finding.trigger_end_event_index == 7
    assert finding.feedback_level == "flag"
    assert finding.reason_code == "UNSAFE_ACTION"
    assert finding.feedback_payload == {
        "source": "cbm",
        "action": "delete",
        "safe": False,
    }


def test_legacy_mapping_can_emit_satisfaction_or_suppress_an_outcome() -> None:
    result = _constraint().evaluate(ExampleState(attempted=True, safe=True))

    assert (
        map_evaluation_to_finding(
            result,
            LegacyFindingMapping(
                violated=LegacyFindingSpec(
                    result_type="constraint_violation",
                    feedback_level="flag",
                    reason_code="UNSAFE_ACTION",
                )
            ),
        )
        is None
    )

    finding = map_evaluation_to_finding(
        result,
        LegacyFindingMapping(
            satisfied=LegacyFindingSpec(
                result_type="success_signal",
                feedback_level="info",
                reason_code="SAFE_ACTION",
            )
        ),
    )

    assert finding is not None
    assert finding.result_type == "success_signal"
    assert finding.reason_code == "SAFE_ACTION"


def test_irrelevant_constraint_never_maps_to_a_finding() -> None:
    result = _constraint().evaluate(ExampleState(attempted=False, safe=False))
    mapping = LegacyFindingMapping(
        satisfied=LegacyFindingSpec(
            result_type="success_signal",
            feedback_level="info",
            reason_code="SAFE_ACTION",
        ),
        violated=LegacyFindingSpec(
            result_type="constraint_violation",
            feedback_level="flag",
            reason_code="UNSAFE_ACTION",
        ),
    )

    assert map_evaluation_to_finding(result, mapping) is None


def test_compatible_constraint_rule_satisfies_current_rule_contract() -> None:
    trace = TraceIndex.build(())
    context = RuleContext(
        trace=trace,
        solution_state=LabSolutionState(trace=trace),
        explanation_signals=(),
    )
    rule: RuleFn = CompatibleConstraintRule(
        constraint=Constraint(
            constraint_id="COMPATIBLE_CONSTRAINT",
            relevance=lambda _context: ConditionResult.true(),
            satisfaction=lambda _context: ConditionResult.false(),
        ),
        finding_mapping=LegacyFindingMapping(
            violated=LegacyFindingSpec(
                result_type="constraint_violation",
                feedback_level="flag",
                reason_code="COMPATIBLE_VIOLATION",
            )
        ),
    )

    findings = rule(context)

    assert len(findings) == 1
    assert findings[0].code == "COMPATIBLE_CONSTRAINT"
