from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Generic, Literal, TypeVar


ContextT = TypeVar("ContextT")
ConstraintStatus = Literal["not_relevant", "satisfied", "violated"]


def _empty_facts() -> Mapping[str, object]:
    return MappingProxyType({})


@dataclass(frozen=True)
class ConstraintEvidence:
    """Trace evidence and normalized facts supporting a condition result."""

    trigger_event_index: int | None = None
    trigger_start_event_index: int | None = None
    trigger_end_event_index: int | None = None
    facts: Mapping[str, object] = field(default_factory=_empty_facts)

    @classmethod
    def build(
        cls,
        *,
        trigger_event_index: int | None = None,
        trigger_start_event_index: int | None = None,
        trigger_end_event_index: int | None = None,
        facts: Mapping[str, object] | None = None,
    ) -> "ConstraintEvidence":
        return cls(
            trigger_event_index=trigger_event_index,
            trigger_start_event_index=trigger_start_event_index,
            trigger_end_event_index=trigger_end_event_index,
            facts=MappingProxyType(dict(facts or {})),
        )


@dataclass(frozen=True)
class ConditionResult:
    """The truth value and evidence produced by one CBM condition."""

    holds: bool
    evidence: ConstraintEvidence | None = None

    @classmethod
    def true(cls, evidence: ConstraintEvidence | None = None) -> "ConditionResult":
        return cls(holds=True, evidence=evidence)

    @classmethod
    def false(cls, evidence: ConstraintEvidence | None = None) -> "ConditionResult":
        return cls(holds=False, evidence=evidence)


ConditionFn = Callable[[ContextT], ConditionResult]


@dataclass(frozen=True)
class ConstraintEvaluation:
    """One CBM constraint's relevance and, when relevant, satisfaction."""

    constraint_id: str
    relevance: ConditionResult
    satisfaction: ConditionResult | None

    def __post_init__(self) -> None:
        if not self.constraint_id.strip():
            raise ValueError("constraint_id must not be empty")
        if self.relevance.holds and self.satisfaction is None:
            raise ValueError("a relevant constraint requires a satisfaction result")
        if not self.relevance.holds and self.satisfaction is not None:
            raise ValueError(
                "an irrelevant constraint must not evaluate its satisfaction condition"
            )

    @property
    def status(self) -> ConstraintStatus:
        if not self.relevance.holds:
            return "not_relevant"
        if self.satisfaction is not None and self.satisfaction.holds:
            return "satisfied"
        return "violated"

    @property
    def evidence(self) -> ConstraintEvidence | None:
        """Prefer satisfaction evidence, falling back to relevance evidence."""

        if self.satisfaction is not None and self.satisfaction.evidence is not None:
            return self.satisfaction.evidence
        return self.relevance.evidence


@dataclass(frozen=True)
class Constraint(Generic[ContextT]):
    """A deterministic CBM relevance/satisfaction pair."""

    constraint_id: str
    relevance: ConditionFn[ContextT]
    satisfaction: ConditionFn[ContextT]

    def __post_init__(self) -> None:
        if not self.constraint_id.strip():
            raise ValueError("constraint_id must not be empty")

    def evaluate(self, context: ContextT) -> ConstraintEvaluation:
        relevance = self.relevance(context)
        if not relevance.holds:
            return ConstraintEvaluation(
                constraint_id=self.constraint_id,
                relevance=relevance,
                satisfaction=None,
            )

        return ConstraintEvaluation(
            constraint_id=self.constraint_id,
            relevance=relevance,
            satisfaction=self.satisfaction(context),
        )
