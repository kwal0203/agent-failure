from typing import Protocol
from uuid import UUID
from .types import SessionMetadataRow


class SessionMetadataRepository(Protocol):
    def get_session_metadata(self, session_id: UUID) -> SessionMetadataRow | None: ...
