"""Ports for learner explanation submission workflow."""

from typing import Protocol

from apps.control_plane.src.application.learner_explanation.ports import (
    LearnerExplanationPort,
)
from apps.control_plane.src.application.session_lifecycle.ports import Outbox
from apps.control_plane.src.application.session_query.ports import (
    SessionMetadataRepository,
)
from apps.control_plane.src.application.trace.ports import TraceEventPort


class SessionExplanationDeps(Protocol):
    @property
    def metadata_repo(self) -> SessionMetadataRepository: ...

    @property
    def learner_explanation_repo(self) -> LearnerExplanationPort: ...

    @property
    def trace_repo(self) -> TraceEventPort: ...

    @property
    def outbox(self) -> Outbox: ...
