from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from apps.evaluator.src.application.types import EvaluatorTraceEvent


@dataclass(frozen=True)
class TraceIndex:
    """Immutable, order-preserving indexes over one evaluator trace window."""

    events: tuple[EvaluatorTraceEvent, ...]
    _by_event_type: Mapping[str, tuple[EvaluatorTraceEvent, ...]] = field(
        repr=False, compare=False
    )
    _by_family: Mapping[str, tuple[EvaluatorTraceEvent, ...]] = field(
        repr=False, compare=False
    )
    _by_family_and_type: Mapping[tuple[str, str], tuple[EvaluatorTraceEvent, ...]] = (
        field(repr=False, compare=False)
    )

    @classmethod
    def build(cls, events: Iterable[EvaluatorTraceEvent]) -> "TraceIndex":
        ordered_events = tuple(events)
        by_event_type: defaultdict[str, list[EvaluatorTraceEvent]] = defaultdict(list)
        by_family: defaultdict[str, list[EvaluatorTraceEvent]] = defaultdict(list)
        by_family_and_type: defaultdict[tuple[str, str], list[EvaluatorTraceEvent]] = (
            defaultdict(list)
        )

        for event in ordered_events:
            by_event_type[event.event_type].append(event)
            by_family[event.family].append(event)
            by_family_and_type[(event.family, event.event_type)].append(event)

        return cls(
            events=ordered_events,
            _by_event_type=MappingProxyType(
                {key: tuple(matched) for key, matched in by_event_type.items()}
            ),
            _by_family=MappingProxyType(
                {key: tuple(matched) for key, matched in by_family.items()}
            ),
            _by_family_and_type=MappingProxyType(
                {key: tuple(matched) for key, matched in by_family_and_type.items()}
            ),
        )

    def of_type(self, event_type: str) -> tuple[EvaluatorTraceEvent, ...]:
        return self._by_event_type.get(event_type, ())

    def of_family(self, family: str) -> tuple[EvaluatorTraceEvent, ...]:
        return self._by_family.get(family, ())

    def of_family_and_type(
        self, *, family: str, event_type: str
    ) -> tuple[EvaluatorTraceEvent, ...]:
        return self._by_family_and_type.get((family, event_type), ())

    def before(
        self, event_index: int, *, inclusive: bool = False
    ) -> tuple[EvaluatorTraceEvent, ...]:
        if inclusive:
            return tuple(
                event for event in self.events if event.event_index <= event_index
            )
        return tuple(event for event in self.events if event.event_index < event_index)

    def after(
        self, event_index: int, *, inclusive: bool = False
    ) -> tuple[EvaluatorTraceEvent, ...]:
        if inclusive:
            return tuple(
                event for event in self.events if event.event_index >= event_index
            )
        return tuple(event for event in self.events if event.event_index > event_index)
