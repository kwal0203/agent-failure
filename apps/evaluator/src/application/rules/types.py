from dataclasses import dataclass
from uuid import UUID
from typing import Callable, Sequence, TypeVar
from apps.evaluator.src.application.types import (
    EvaluatorFinding,
    EvaluatorTraceEvent,
    ExplanationSignal,
)

from .solution_states import LabSolutionState
from .trace_index import TraceIndex


SolutionStateT = TypeVar("SolutionStateT", bound=LabSolutionState)


@dataclass(frozen=True)
class RuleContext:
    trace: TraceIndex
    solution_state: LabSolutionState
    explanation_signals: Sequence[ExplanationSignal]

    @property
    def events(self) -> tuple[EvaluatorTraceEvent, ...]:
        """Ordered trace compatibility view for rules awaiting CBM migration."""

        return self.trace.events

    def require_solution_state(
        self, state_type: type[SolutionStateT]
    ) -> SolutionStateT:
        if not isinstance(self.solution_state, state_type):
            raise TypeError(
                "Rule bundle produced "
                f"{type(self.solution_state).__name__}; expected {state_type.__name__}"
            )
        return self.solution_state


RuleFn = Callable[[RuleContext], tuple[EvaluatorFinding, ...]]
SolutionStateBuilder = Callable[[TraceIndex], LabSolutionState]


@dataclass(frozen=True)
class RuleBundle:
    name: str
    lab_id: UUID
    lab_version_id: UUID
    rule_bundle_version: int
    solution_state_type: type[LabSolutionState]
    build_solution_state: SolutionStateBuilder
    rules: tuple[RuleFn, ...]

    def run(
        self,
        events: Sequence[EvaluatorTraceEvent],
        explanation_signals: Sequence[ExplanationSignal],
    ) -> tuple[EvaluatorFinding, ...]:
        trace = TraceIndex.build(events)
        solution_state = self.build_solution_state(trace)
        if not isinstance(solution_state, self.solution_state_type):
            raise TypeError(
                f"Rule bundle {self.name} produced "
                f"{type(solution_state).__name__}; expected "
                f"{self.solution_state_type.__name__}"
            )
        ctx = RuleContext(
            trace=trace,
            solution_state=solution_state,
            explanation_signals=explanation_signals,
        )
        findings: list[EvaluatorFinding] = []
        for rule in self.rules:
            findings.extend(rule(ctx))

        # TODO(lab1-outcomes): Apply outcome normalization/precedence so evaluator
        # can emit one dominant learner outcome when multiple findings coexist.
        return tuple(findings)
