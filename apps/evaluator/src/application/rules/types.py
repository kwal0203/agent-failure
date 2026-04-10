from dataclasses import dataclass
from uuid import UUID
from typing import Callable, Sequence
from apps.evaluator.src.application.types import (
    EvaluatorFinding,
    EvaluatorTraceEvent,
    ExplanationSignal,
)


@dataclass(frozen=True)
class RuleContext:
    events: Sequence[EvaluatorTraceEvent]
    explanation_signals: Sequence[ExplanationSignal]


RuleFn = Callable[[RuleContext], tuple[EvaluatorFinding, ...]]


@dataclass(frozen=True)
class RuleBundle:
    name: str
    lab_id: UUID
    lab_version_id: UUID
    lab_difficulty: str
    evaluator_version: int
    rules: tuple[RuleFn, ...]

    def run(
        self,
        events: Sequence[EvaluatorTraceEvent],
        explanation_signals: Sequence[ExplanationSignal],
    ) -> tuple[EvaluatorFinding, ...]:
        ctx = RuleContext(events=events, explanation_signals=explanation_signals)
        findings: list[EvaluatorFinding] = []
        for rule in self.rules:
            findings.extend(rule(ctx))

        # TODO(lab1-outcomes): Apply outcome normalization/precedence so evaluator
        # can emit one dominant learner outcome when multiple findings coexist.
        return tuple(findings)
