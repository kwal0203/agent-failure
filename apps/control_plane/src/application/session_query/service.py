from apps.control_plane.src.application.session_query.ports import (
    SessionMetadataRepository,
)
from apps.control_plane.src.application.common.types import PrincipalContext
from uuid import UUID
from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState

from .errors import ForbiddenErrorSessionQuery
from .types import SessionMetadataDTO, SessionObjectiveDTO


def derive_interactive(state: str) -> bool:
    return state in {SessionState.ACTIVE.value, SessionState.IDLE.value}


def get_session_metadata(
    session_id: UUID,
    principal: PrincipalContext,
    repo: SessionMetadataRepository,
) -> SessionMetadataDTO | None:

    row = repo.get_session_metadata(session_id=session_id)
    if row is None:
        return None

    metadata = row.metadata
    objectives: list[SessionObjectiveDTO] = []
    for objective in row.objectives:
        objectives.append(
            SessionObjectiveDTO(
                objective_key=objective.objective_key,
                label=objective.label,
                status=objective.status,
                completed_at=objective.completed_at,
                updated_at=objective.updated_at,
            )
        )

    is_owner = metadata.owner_user_id == principal.user_id
    is_admin = principal.role == "admin"
    if not (is_owner or is_admin):
        raise ForbiddenErrorSessionQuery(role=principal.role)

    return SessionMetadataDTO(
        id=metadata.id,
        lab_id=metadata.lab_id,
        lab_version_id=metadata.lab_version_id,
        owner_user_id=metadata.owner_user_id,
        state=metadata.state,
        runtime_substate=metadata.runtime_substate,
        resume_mode=metadata.resume_mode,
        last_transition_reason=metadata.last_transition_reason,
        interactive=derive_interactive(metadata.state),
        created_at=metadata.created_at,
        started_at=metadata.started_at,
        ended_at=metadata.ended_at,
        lab_difficulty=metadata.lab_difficulty,
        progress_chips=objectives,
    )
