from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal

from apps.evaluator.src.application.pedagogy.policy import (
    PedagogicalPolicy,
)
from apps.evaluator.src.application.types import EvaluatorFinding

from .cbm import (
    ConditionResult,
    Constraint,
    ConstraintEvaluation,
    ConstraintEvidence,
)
from .types import RuleContext


def map_evaluation_to_finding(
    evaluation: ConstraintEvaluation,
    pedagogical_policy: PedagogicalPolicy,
) -> EvaluatorFinding | None:
    """Apply pedagogical policy to the assessment result."""

    outcome_policy = pedagogical_policy.outcome_policy_for(evaluation.constraint_id)
    spec = outcome_policy.presentation_for(evaluation.status)
    if spec is None:
        return None

    evidence = evaluation.evidence
    feedback_payload = dict(spec.feedback_payload)
    if evidence is not None:
        feedback_payload.update(evidence.facts)

    return EvaluatorFinding(
        result_type=spec.result_type,
        code=evaluation.constraint_id,
        trigger_event_index=(
            evidence.trigger_event_index if evidence is not None else None
        ),
        trigger_start_event_index=(
            evidence.trigger_start_event_index if evidence is not None else None
        ),
        trigger_end_event_index=(
            evidence.trigger_end_event_index if evidence is not None else None
        ),
        feedback_level=spec.feedback_level,
        reason_code=spec.reason_code,
        feedback_payload=feedback_payload,
    )


@dataclass(frozen=True)
class CompatibleConstraintRule:
    """Callable bridge allowing CBM constraints in the current rule bundles."""

    constraint: Constraint[RuleContext]
    pedagogical_policy: PedagogicalPolicy
    observe_each: Callable[[RuleContext], Iterable[ConstraintEvidence]] | None = None

    def __call__(self, context: RuleContext) -> tuple[EvaluatorFinding, ...]:
        if self.observe_each is not None:
            findings: list[EvaluatorFinding] = []
            for evidence in self.observe_each(context):
                relevance = ConditionResult.true(evidence)
                evaluation = ConstraintEvaluation(
                    constraint_id=self.constraint.constraint_id,
                    relevance=relevance,
                    satisfaction=self.constraint.satisfaction(context),
                )
                finding = map_evaluation_to_finding(evaluation, self.pedagogical_policy)
                if finding is not None:
                    findings.append(finding)
            return tuple(findings)

        finding = map_evaluation_to_finding(
            self.constraint.evaluate(context), self.pedagogical_policy
        )
        return (finding,) if finding is not None else ()


ObservedConstraintOutcome = Literal["satisfied", "violated"]
EvidenceObserver = Callable[[RuleContext], ConstraintEvidence | None]


def compatible_observed_constraint_rule(
    *,
    constraint_id: str,
    observe: EvidenceObserver,
    outcome: ObservedConstraintOutcome,
    pedagogical_policy: PedagogicalPolicy,
) -> CompatibleConstraintRule:
    """Build a current-contract rule for an observed CBM constraint outcome."""

    def relevance(context: RuleContext) -> ConditionResult:
        evidence = observe(context)
        if evidence is None:
            return ConditionResult.false()
        return ConditionResult.true(evidence)

    def satisfaction(_context: RuleContext) -> ConditionResult:
        return ConditionResult(holds=outcome == "satisfied")

    return CompatibleConstraintRule(
        constraint=Constraint(
            constraint_id=constraint_id,
            relevance=relevance,
            satisfaction=satisfaction,
        ),
        pedagogical_policy=pedagogical_policy,
    )


RepeatedEvidenceObserver = Callable[[RuleContext], tuple[ConstraintEvidence, ...]]


def compatible_repeated_observed_constraint_rule(
    *,
    constraint_id: str,
    observe_each: RepeatedEvidenceObserver,
    outcome: ObservedConstraintOutcome,
    pedagogical_policy: PedagogicalPolicy,
) -> CompatibleConstraintRule:
    """Build a CBM rule that preserves one finding per observed occurrence."""

    def relevance(context: RuleContext) -> ConditionResult:
        observations = observe_each(context)
        if not observations:
            return ConditionResult.false()
        return ConditionResult.true(observations[0])

    def satisfaction(_context: RuleContext) -> ConditionResult:
        return ConditionResult(holds=outcome == "satisfied")

    return CompatibleConstraintRule(
        constraint=Constraint(
            constraint_id=constraint_id,
            relevance=relevance,
            satisfaction=satisfaction,
        ),
        pedagogical_policy=pedagogical_policy,
        observe_each=observe_each,
    )
