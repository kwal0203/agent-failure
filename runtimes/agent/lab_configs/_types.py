from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID
from typing import Callable, Literal

from apps.agent_harness.src.application.session_loop.types import MemoryType
from runtimes.agent.hooks import AgentLabHooks


@dataclass(frozen=True)
class SeedFilesConfig:
    path: str
    content: str


@dataclass(frozen=True)
class SeedMemoryConfig:
    memory_type: MemoryType
    content: str
    metadata: dict[str, str]
    source_artifact_id: str
    source_artifact_type: str
    provenance_trust: Literal["trusted", "untrusted"] = "untrusted"


@dataclass(frozen=True)
class SeedConfig:
    files: tuple[SeedFilesConfig, ...] = ()
    memory: tuple[SeedMemoryConfig, ...] = ()


@dataclass(frozen=True)
class LabConfig:
    lab_id: UUID
    slug: str
    system_prompt: str
    enabled_tools: tuple[str, ...] = field(default_factory=tuple)
    seed: SeedConfig | None = None
    hooks_factory: Callable[[], AgentLabHooks] | None = None
