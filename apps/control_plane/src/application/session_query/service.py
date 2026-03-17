from apps.control_plane.src.application.session_query.ports import (
    SessionMetadataRepository,
)
from uuid import UUID
from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState

from .errors import ForbiddenErrorSessionQuery
from .types import SessionMetadataDTO


def derive_interactive(state: str) -> bool:
    return state in {SessionState.ACTIVE.value, SessionState.IDLE.value}


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

    return SessionMetadataDTO(
        id=row.id,
        lab_id=row.lab_id,
        lab_version_id=row.lab_version_id,
        owner_user_id=row.owner_user_id,
        state=row.state,
        runtime_substate=row.runtime_substate,
        resume_mode=row.resume_mode,
        interactive=derive_interactive(state=row.state),
        created_at=row.created_at,
        started_at=row.started_at,
        ended_at=row.ended_at,
    )
