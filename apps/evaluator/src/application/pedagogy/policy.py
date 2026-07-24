from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from apps.evaluator.src.application.rules.cbm import ConstraintStatus
from apps.evaluator.src.application.types import FeedbackLevel, ResultType


def _empty_payload() -> Mapping[str, object]:
    return MappingProxyType({})


@dataclass(frozen=True)
class FindingPresentation:
    """How an assessed constraint outcome is exposed by the current API."""

    result_type: ResultType
    feedback_level: FeedbackLevel
    reason_code: str
    feedback_payload: Mapping[str, object] = field(default_factory=_empty_payload)

    def __post_init__(self) -> None:
        if not self.reason_code.strip():
            raise ValueError("reason_code must not be empty")
        object.__setattr__(
            self,
            "feedback_payload",
            MappingProxyType(dict(self.feedback_payload)),
        )


@dataclass(frozen=True)
class ConstraintOutcomePolicy:
    """Selects which outcomes are learner-visible and how they are classified."""

    satisfied: FindingPresentation | None = None
    violated: FindingPresentation | None = None

    def presentation_for(self, status: ConstraintStatus) -> FindingPresentation | None:
        if status == "satisfied":
            return self.satisfied
        if status == "violated":
            return self.violated
        return None


@dataclass(frozen=True)
class PedagogicalPolicy:
    """Versioned presentation policy kept separate from assessment rules."""

    name: str
    outcomes_by_constraint_id: Mapping[str, ConstraintOutcomePolicy]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("pedagogical policy name must not be empty")
        if not self.outcomes_by_constraint_id:
            raise ValueError("pedagogical policy must contain at least one constraint")
        if any(
            not constraint_id.strip()
            for constraint_id in self.outcomes_by_constraint_id
        ):
            raise ValueError("constraint IDs must not be empty")

        object.__setattr__(
            self,
            "outcomes_by_constraint_id",
            MappingProxyType(dict(self.outcomes_by_constraint_id)),
        )

    @classmethod
    def build(
        cls,
        *,
        name: str,
        outcomes_by_constraint_id: Mapping[str, ConstraintOutcomePolicy],
    ) -> "PedagogicalPolicy":
        return cls(
            name=name,
            outcomes_by_constraint_id=outcomes_by_constraint_id,
        )

    def outcome_policy_for(self, constraint_id: str) -> ConstraintOutcomePolicy:
        try:
            return self.outcomes_by_constraint_id[constraint_id]
        except KeyError as exc:
            raise KeyError(
                f"pedagogical policy {self.name!r} does not define "
                f"constraint {constraint_id!r}"
            ) from exc
