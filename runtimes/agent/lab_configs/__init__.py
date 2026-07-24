from __future__ import annotations

from uuid import UUID

from apps.contracts.src.lab_identities import (
    AGENT_MEMORY_POISONING,
    AGENT_PROMPT_INJECTION,
    AGENT_TOOL_MISUSE,
)

from ._types import LabConfig
from .lab_001_prompt_injection import LAB_001_CONFIG
from .lab_002_tool_misuse import LAB_002_CONFIG
from .lab_003_memory_poisoning import LAB_003_CONFIG

__all__ = [
    "LabConfig",
    "SeedConfig",
    "SeedFilesConfig",
    "SeedMemoryConfig",
    "load_lab_config",
    "all_lab_configs",
]

from ._types import SeedConfig, SeedFilesConfig, SeedMemoryConfig

_BASE_CONFIGS: dict[UUID, LabConfig] = {
    LAB_001_CONFIG.lab_id: LAB_001_CONFIG,
    LAB_002_CONFIG.lab_id: LAB_002_CONFIG,
    LAB_003_CONFIG.lab_id: LAB_003_CONFIG,
}

_AGENT_ALIASES: dict[UUID, LabConfig] = {
    AGENT_PROMPT_INJECTION.lab_id: LAB_001_CONFIG,
    AGENT_TOOL_MISUSE.lab_id: LAB_002_CONFIG,
    AGENT_MEMORY_POISONING.lab_id: LAB_003_CONFIG,
}

_ALL_CONFIGS: dict[UUID, LabConfig] = {**_BASE_CONFIGS, **_AGENT_ALIASES}


def load_lab_config(lab_id: UUID) -> LabConfig | None:
    return _ALL_CONFIGS.get(lab_id)


def all_lab_configs() -> dict[UUID, LabConfig]:
    return dict(_ALL_CONFIGS)
