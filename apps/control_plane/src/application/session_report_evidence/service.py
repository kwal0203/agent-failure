from collections.abc import Sequence
from uuid import UUID

from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.trace.ports import TraceEventPort

from .errors import (
    ForbiddenErrorSessionReportEvidence,
    InvalidSessionReportEvidenceError,
    SessionNotFoundErrorSessionReportEvidence,
)
from .ports import SessionReportEvidenceRepositoryPort
from .types import SessionReportEvidenceItemInput, SessionReportEvidenceRow

_REPORT_SELECTABLE_TRACE_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "MALICIOUS_EMAIL_READ",
        "TOKEN_DISCLOSURE_ATTEMPTED",
        "TOKEN_DISCLOSED",
        "ATTACK_EMAIL_SENT",
        "TOOL_CALL_REQUESTED",
        "TOOL_CALL_SUCCEEDED",
        "TOOL_CALL_FAILED",
        "MODEL_TURN_FAILED",
        "RUNTIME_PROVISION_FAILED",
    }
)


def _require_owner_or_admin(
    *,
    session_id: UUID,
    principal: PrincipalContext,
    repo: SessionReportEvidenceRepositoryPort,
) -> None:
    owner_user_id = repo.get_session_owner_user_id(session_id=session_id)
    if owner_user_id is None:
        raise SessionNotFoundErrorSessionReportEvidence()

    is_owner = owner_user_id == principal.user_id
    is_admin = principal.role == "admin"
    if not (is_owner or is_admin):
        raise ForbiddenErrorSessionReportEvidence(role=principal.role)


def get_session_report_evidence(
    *,
    session_id: UUID,
    principal: PrincipalContext,
    repo: SessionReportEvidenceRepositoryPort,
) -> tuple[SessionReportEvidenceRow, ...]:
    _require_owner_or_admin(session_id=session_id, principal=principal, repo=repo)
    rows = repo.list_report_evidence_for_session(session_id=session_id)
    return tuple(rows)


def replace_session_report_evidence(
    *,
    session_id: UUID,
    principal: PrincipalContext,
    items: Sequence[SessionReportEvidenceItemInput],
    repo: SessionReportEvidenceRepositoryPort,
    trace_repo: TraceEventPort,
    enforce_selectable_only: bool = True,
) -> tuple[SessionReportEvidenceItemInput, ...]:
    _require_owner_or_admin(session_id=session_id, principal=principal, repo=repo)

    trace_events = trace_repo.list_trace_events_for_session(session_id=session_id)
    trace_event_types_by_id = {
        event.event_id: event.event_type for event in trace_events
    }

    seen_event_ids: set[UUID] = set()
    normalized_items: list[SessionReportEvidenceItemInput] = []

    for position, item in enumerate(items):
        if item.event_id in seen_event_ids:
            raise InvalidSessionReportEvidenceError(
                message="duplicate event_id in report evidence payload",
                details={
                    "session_id": str(session_id),
                    "event_id": str(item.event_id),
                },
            )
        seen_event_ids.add(item.event_id)

        event_type = trace_event_types_by_id.get(item.event_id)
        if event_type is None:
            raise InvalidSessionReportEvidenceError(
                message="event_id does not belong to session trace",
                details={
                    "session_id": str(session_id),
                    "event_id": str(item.event_id),
                },
            )

        if (
            enforce_selectable_only
            and event_type not in _REPORT_SELECTABLE_TRACE_EVENT_TYPES
        ):
            raise InvalidSessionReportEvidenceError(
                message="event_id is not report-selectable",
                details={
                    "session_id": str(session_id),
                    "event_id": str(item.event_id),
                    "event_type": event_type,
                },
            )

        normalized_items.append(
            SessionReportEvidenceItemInput(
                event_id=item.event_id,
                position=position,
                title=item.title,
                description=item.description,
                occurred_at=item.occurred_at,
                evidence_type=item.evidence_type,
                objective_keys=item.objective_keys,
                why_it_matters=item.why_it_matters,
                default_priority=item.default_priority,
                student_note=item.student_note,
            )
        )

    repo.replace_report_evidence_for_session(
        session_id=session_id,
        items=normalized_items,
    )
    return tuple(normalized_items)
