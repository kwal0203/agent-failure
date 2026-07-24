from collections.abc import Callable
from dataclasses import dataclass, replace

from apps.evaluator.src.application.pedagogy.policy import PedagogicalPolicy
from apps.evaluator.src.application.types import EvaluatorFinding

from .cbm import (
    ConditionResult,
    Constraint,
    ConstraintEvaluation,
    ConstraintEvidence,
)
from .types import RuleContext


EvidenceObserver = Callable[[RuleContext], ConstraintEvidence | None]
RepeatedEvidenceObserver = Callable[[RuleContext], tuple[ConstraintEvidence, ...]]


def map_evaluation_to_finding(
    evaluation: ConstraintEvaluation,
    pedagogical_policy: PedagogicalPolicy,
) -> EvaluatorFinding | None:
    """Apply learner-facing policy to an independently assessed constraint."""

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
class ConstraintRule:
    """Evaluate one CBM constraint and project it through pedagogical policy."""

    constraint: Constraint[RuleContext]
    pedagogical_policy: PedagogicalPolicy

    def __call__(self, context: RuleContext) -> tuple[EvaluatorFinding, ...]:
        finding = map_evaluation_to_finding(
            self.constraint.evaluate(context), self.pedagogical_policy
        )
        return (finding,) if finding is not None else ()


@dataclass(frozen=True)
class RepeatedConstraintRule:
    """Project one independently assessed outcome for each evidence occurrence."""

    constraint: Constraint[RuleContext]
    pedagogical_policy: PedagogicalPolicy
    evidence_each: RepeatedEvidenceObserver

    def __call__(self, context: RuleContext) -> tuple[EvaluatorFinding, ...]:
        evaluation = self.constraint.evaluate(context)
        if evaluation.status == "not_relevant":
            return ()

        evidence_items = self.evidence_each(context)
        if not evidence_items:
            finding = map_evaluation_to_finding(evaluation, self.pedagogical_policy)
            return (finding,) if finding is not None else ()

        findings: list[EvaluatorFinding] = []
        for evidence in evidence_items:
            finding = map_evaluation_to_finding(
                _with_outcome_evidence(evaluation, evidence),
                self.pedagogical_policy,
            )
            if finding is not None:
                findings.append(finding)
        return tuple(findings)


def _with_outcome_evidence(
    evaluation: ConstraintEvaluation,
    evidence: ConstraintEvidence,
) -> ConstraintEvaluation:
    satisfaction = evaluation.satisfaction
    if satisfaction is None:
        return evaluation
    return replace(
        evaluation,
        satisfaction=replace(satisfaction, evidence=evidence),
    )


def observed(
    observe: EvidenceObserver,
) -> Callable[[RuleContext], ConditionResult]:
    """Build a condition that holds when normalized evidence is observed."""

    def condition(context: RuleContext) -> ConditionResult:
        evidence = observe(context)
        return ConditionResult(holds=evidence is not None, evidence=evidence)

    return condition


def not_observed(
    observe: EvidenceObserver,
) -> Callable[[RuleContext], ConditionResult]:
    """Build a prohibition that holds only while its evidence is absent."""

    def condition(context: RuleContext) -> ConditionResult:
        evidence = observe(context)
        return ConditionResult(holds=evidence is None, evidence=evidence)

    return condition


def any_observed(
    observe_each: RepeatedEvidenceObserver,
) -> Callable[[RuleContext], ConditionResult]:
    """Build a condition that holds when at least one occurrence is observed."""

    def condition(context: RuleContext) -> ConditionResult:
        evidence_items = observe_each(context)
        evidence = evidence_items[0] if evidence_items else None
        return ConditionResult(holds=bool(evidence_items), evidence=evidence)

    return condition


def none_observed(
    observe_each: RepeatedEvidenceObserver,
) -> Callable[[RuleContext], ConditionResult]:
    """Build a prohibition that holds while no occurrence is observed."""

    def condition(context: RuleContext) -> ConditionResult:
        evidence_items = observe_each(context)
        evidence = evidence_items[0] if evidence_items else None
        return ConditionResult(holds=not evidence_items, evidence=evidence)

    return condition
