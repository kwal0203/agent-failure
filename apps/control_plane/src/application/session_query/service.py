from apps.control_plane.src.application.session_query.ports import (
    SessionListByLabRepository,
    SessionMetadataRepository,
    SessionLatestByLabRepository,
)
from apps.control_plane.src.application.common.types import PrincipalContext
from uuid import UUID
from apps.control_plane.src.domain.session_lifecycle.state_machine import SessionState

from .errors import ForbiddenErrorSessionQuery
from .types import (
    SessionFeedbackDTO,
    SessionHintDTO,
    SessionMetadataDTO,
    SessionObjectiveDTO,
    SessionSummaryDTO,
)


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
    hints: list[SessionHintDTO] = []
    unread_hint_count = 0
    for hint in row.hints:
        hints.append(
            SessionHintDTO(
                hint_key=hint.hint_key,
                text=hint.text,
                sort_order=hint.sort_order,
                status=hint.status,
                unlock_at=hint.unlock_at,
                unlocked_at=hint.unlocked_at,
                seen_at=hint.seen_at,
            )
        )
        if hint.status == "unlocked" and hint.seen_at is None:
            unread_hint_count += 1
    feedback: list[SessionFeedbackDTO] = []
    unread_feedback_count = 0
    for feedback_item in row.feedback:
        feedback.append(
            SessionFeedbackDTO(
                id=feedback_item.id,
                feedback_key=feedback_item.feedback_key,
                reason_code=feedback_item.reason_code,
                message=feedback_item.message,
                severity=feedback_item.severity,
                trigger_event_index=feedback_item.trigger_event_index,
                created_at=feedback_item.created_at,
                seen_at=feedback_item.seen_at,
            )
        )
        if feedback_item.seen_at is None:
            unread_feedback_count += 1

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
        completion_status=metadata.completion_status,
        completed_at=metadata.completed_at,
        completion_reason_code=metadata.completion_reason_code,
        lab_difficulty=metadata.lab_difficulty,
        progress_chips=objectives,
        hints=hints,
        unread_hint_count=unread_hint_count,
        feedback_items=feedback,
        feedback=feedback,
        unread_feedback_count=unread_feedback_count,
    )


def get_latest_session_id_for_lab(
    *,
    lab_id: UUID,
    principal: PrincipalContext,
    repo: SessionLatestByLabRepository,
) -> UUID | None:
    owner_user_id = None if principal.role == "admin" else principal.user_id
    return repo.get_latest_session_id_for_lab(
        lab_id=lab_id,
        owner_user_id=owner_user_id,
    )


def list_sessions_for_lab(
    *,
    lab_id: UUID,
    principal: PrincipalContext,
    repo: SessionListByLabRepository,
    limit: int = 1,
) -> tuple[SessionSummaryDTO, ...]:
    owner_user_id = None if principal.role == "admin" else principal.user_id
    rows = repo.list_sessions_for_lab(
        lab_id=lab_id,
        owner_user_id=owner_user_id,
        limit=limit,
    )
    return tuple(
        SessionSummaryDTO(
            session_id=row.session_id,
            lab_id=row.lab_id,
            created_at=row.created_at,
            state=row.state,
            completion_status=row.completion_status,
        )
        for row in rows
    )
