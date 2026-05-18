from typing import Protocol
from uuid import UUID
from .types import SessionMetadataBundleRow, SessionSummaryRow


class SessionMetadataRepository(Protocol):
    def get_session_metadata(
        self, session_id: UUID
    ) -> SessionMetadataBundleRow | None: ...


class SessionLatestByLabRepository(Protocol):
    def get_latest_session_id_for_lab(
        self, *, lab_id: UUID, owner_user_id: UUID | None
    ) -> UUID | None: ...


class SessionListByLabRepository(Protocol):
    def list_sessions_for_lab(
        self, *, lab_id: UUID, owner_user_id: UUID | None, limit: int
    ) -> tuple[SessionSummaryRow, ...]: ...
