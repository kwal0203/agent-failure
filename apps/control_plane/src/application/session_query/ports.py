from typing import Protocol
from uuid import UUID
from .types import SessionMetadataBundleRow


class SessionMetadataRepository(Protocol):
    def get_session_metadata(
        self, session_id: UUID
    ) -> SessionMetadataBundleRow | None: ...
