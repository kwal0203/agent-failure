from dataclasses import dataclass


@dataclass(frozen=True)
class DifficultyConfig:
    system_prompt: str
