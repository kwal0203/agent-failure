from apps.control_plane.src.application.session_query.ports import (
    SessionMetadataRepository,
)
from .ports import SessionMetadataDTO
from uuid import UUID


def get_session_metadata(
    session_id: UUID, repo: SessionMetadataRepository
) -> SessionMetadataDTO | None:
    result = repo.get_session_metadata(session_id=session_id)
    return result
