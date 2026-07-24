from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal

from apps.evaluator.src.application.types import (
    EvaluatorFinding,
    FeedbackLevel,
    ResultType,
)

from .cbm import (
    ConditionResult,
    Constraint,
    ConstraintEvaluation,
    ConstraintEvidence,
    ConstraintStatus,
)
from .types import RuleContext


def _empty_payload() -> Mapping[str, object]:
    return MappingProxyType({})


@dataclass(frozen=True)
class LegacyFindingSpec:
    """Temporary projection metadata for the pre-CBM finding contract."""

    result_type: ResultType
    feedback_level: FeedbackLevel
    reason_code: str
    feedback_payload: Mapping[str, object] = field(default_factory=_empty_payload)

    def __post_init__(self) -> None:
        if not self.reason_code.strip():
            raise ValueError("reason_code must not be empty")


@dataclass(frozen=True)
class LegacyFindingMapping:
    """Selects which CBM outcomes remain visible as legacy findings."""

    satisfied: LegacyFindingSpec | None = None
    violated: LegacyFindingSpec | None = None

    def for_status(self, status: ConstraintStatus) -> LegacyFindingSpec | None:
        if status == "satisfied":
            return self.satisfied
        if status == "violated":
            return self.violated
        return None


def map_evaluation_to_finding(
    evaluation: ConstraintEvaluation,
    mapping: LegacyFindingMapping,
) -> EvaluatorFinding | None:
    """Project a CBM result onto the existing persistence/API contract."""

    spec = mapping.for_status(evaluation.status)
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
    finding_mapping: LegacyFindingMapping

    def __call__(self, context: RuleContext) -> tuple[EvaluatorFinding, ...]:
        finding = map_evaluation_to_finding(
            self.constraint.evaluate(context), self.finding_mapping
        )
        return (finding,) if finding is not None else ()


ObservedConstraintOutcome = Literal["satisfied", "violated"]
EvidenceObserver = Callable[[RuleContext], ConstraintEvidence | None]


def compatible_observed_constraint_rule(
    *,
    constraint_id: str,
    observe: EvidenceObserver,
    outcome: ObservedConstraintOutcome,
    finding: LegacyFindingSpec,
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
        finding_mapping=LegacyFindingMapping(
            satisfied=finding if outcome == "satisfied" else None,
            violated=finding if outcome == "violated" else None,
        ),
    )
