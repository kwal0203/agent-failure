from typing import Protocol
from uuid import UUID

from .types import HintTemplate


class LabHintTemplateReaderPort(Protocol):
    def list_hint_templates(self, lab_version_id: UUID) -> list[HintTemplate]:
        """
        Return active hint templates for a lab version in display/unlock order.
        """
        ...
