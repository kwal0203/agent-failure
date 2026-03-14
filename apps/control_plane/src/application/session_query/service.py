from apps.control_plane.src.application.session_query.ports import (
    SessionMetadataRepository,
)
from uuid import UUID

from .ports import SessionMetadataDTO
from .errors import ForbiddenErrorSessionQuery


def get_session_metadata(
    session_id: UUID,
    principal_user_id: UUID,
    principal_user_role: str,
    repo: SessionMetadataRepository,
) -> SessionMetadataDTO | None:

    row = repo.get_session_metadata(session_id=session_id)
    if row is None:
        return None
    is_owner = row.owner_user_id == principal_user_id
    is_admin = principal_user_role == "admin"
    if not (is_owner or is_admin):
        raise ForbiddenErrorSessionQuery(role=principal_user_role)

    return row
