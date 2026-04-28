from __future__ import annotations

from uuid import UUID

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

_AGENT_LAB_1_ID = UUID("44444444-4444-4444-4444-444444444444")
_AGENT_LAB_2_ID = UUID("55555555-5555-5555-5555-555555555555")
_AGENT_LAB_3_ID = UUID("66666666-6666-6666-6666-666666666666")

_BASE_CONFIGS: dict[UUID, LabConfig] = {
    LAB_001_CONFIG.lab_id: LAB_001_CONFIG,
    LAB_002_CONFIG.lab_id: LAB_002_CONFIG,
    LAB_003_CONFIG.lab_id: LAB_003_CONFIG,
}

_AGENT_ALIASES: dict[UUID, LabConfig] = {
    _AGENT_LAB_1_ID: LAB_001_CONFIG,
    _AGENT_LAB_2_ID: LAB_002_CONFIG,
    _AGENT_LAB_3_ID: LAB_003_CONFIG,
}

_ALL_CONFIGS: dict[UUID, LabConfig] = {**_BASE_CONFIGS, **_AGENT_ALIASES}


def load_lab_config(lab_id: UUID) -> LabConfig | None:
    return _ALL_CONFIGS.get(lab_id)


def all_lab_configs() -> dict[UUID, LabConfig]:
    return dict(_ALL_CONFIGS)
