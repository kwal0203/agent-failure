from dataclasses import dataclass
from uuid import UUID
from typing import Callable, Sequence
from apps.evaluator.src.application.types import EvaluatorFinding, EvaluatorTraceEvent


RuleFn = Callable[[EvaluatorTraceEvent], EvaluatorFinding | None]


@dataclass(frozen=True)
class RuleBundle:
    name: str
    lab_id: UUID
    lab_version_id: UUID
    evaluator_version: int
    rules: tuple[RuleFn, ...]

    def run(
        self, events: Sequence[EvaluatorTraceEvent]
    ) -> tuple[EvaluatorFinding, ...]:
        findings: list[EvaluatorFinding] = []
        for event in events:
            for rule in self.rules:
                finding = rule(event)
                if finding is not None:
                    findings.append(finding)

        return tuple(findings)
