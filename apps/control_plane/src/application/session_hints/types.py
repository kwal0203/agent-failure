from dataclasses import dataclass


@dataclass(frozen=True)
class HintTemplate:
    hint_key: str
    text: str
    offset_seconds: int
    sort_order: int
