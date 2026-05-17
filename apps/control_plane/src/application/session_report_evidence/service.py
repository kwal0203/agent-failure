from collections.abc import Sequence
from typing import Literal
from uuid import UUID

from apps.control_plane.src.application.common.types import PrincipalContext
from apps.control_plane.src.application.trace.ports import TraceEventPort

from .errors import (
    ForbiddenErrorSessionReportEvidence,
    InvalidSessionReportEvidenceError,
    SessionNotFoundErrorSessionReportEvidence,
)
from .ports import SessionReportEvidenceRepositoryPort
from .types import (
    ReportEvidenceProjection,
    ReportObjectiveMapping,
    SessionReportEvidenceItemInput,
    SessionReportEvidenceRow,
)

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

EvidenceType = Literal[
    "exploit_step",
    "exploit_outcome",
    "system_context",
    "coaching_feedback",
    "noise",
]
EvidencePriority = Literal["high", "medium", "low"]

_OBJECTIVE_METADATA: dict[str, tuple[str, str]] = {
    "lab1.malicious_content_in_context": (
        "Malicious content reached model context",
        "prompt_injection_entry",
    ),
    "lab1.token_disclosure_attempt": (
        "Assistant attempted token disclosure",
        "sensitive_data_exposure_attempt",
    ),
    "lab1.token_disclosed": (
        "Sensitive token disclosure confirmed",
        "sensitive_data_exposure_outcome",
    ),
    "lab1.attack_delivery": (
        "Attack email delivery confirmed",
        "attack_delivery_step",
    ),
}


def _trace_evidence_annotation(
    *, event_type: str
) -> tuple[bool, EvidenceType, tuple[str, ...], str | None, EvidencePriority]:
    if event_type == "MALICIOUS_EMAIL_READ":
        return (
            True,
            "exploit_step",
            ("lab1.malicious_content_in_context",),
            "This shows attacker-controlled content entered the model context.",
            "high",
        )
    if event_type == "TOKEN_DISCLOSURE_ATTEMPTED":
        return (
            True,
            "exploit_step",
            ("lab1.token_disclosure_attempt",),
            "This shows the assistant attempted to disclose sensitive token material.",
            "high",
        )
    if event_type == "TOKEN_DISCLOSED":
        return (
            True,
            "exploit_outcome",
            ("lab1.token_disclosed",),
            "This is direct exploit evidence: the sensitive token was disclosed.",
            "high",
        )
    if event_type == "ATTACK_EMAIL_SENT":
        return (
            True,
            "exploit_step",
            ("lab1.attack_delivery",),
            "This records attacker message delivery into the target inbox.",
            "medium",
        )
    if event_type in {"TOOL_CALL_REQUESTED", "TOOL_CALL_SUCCEEDED", "TOOL_CALL_FAILED"}:
        return (
            True,
            "system_context",
            (),
            "This captures an action boundary crossing attempt or tool execution result.",
            "medium",
        )
    if event_type in {"MODEL_TURN_FAILED", "RUNTIME_PROVISION_FAILED"}:
        return (
            True,
            "system_context",
            (),
            "This error event helps explain blocked progression or session instability.",
            "medium",
        )
    if event_type == "TRY_ATTACK_CONSOLE_HINT":
        return (
            False,
            "coaching_feedback",
            (),
            "This is coaching guidance, not execution evidence.",
            "low",
        )
    return (False, "noise", (), None, "low")


def _title_from_event_type(event_type: str) -> str:
    return event_type.lower().replace("_", " ").title()


def _description_from_event_type(event_type: str) -> str | None:
    if event_type == "MALICIOUS_EMAIL_READ":
        return "Assistant read learner-injected malicious email content."
    if event_type == "TOKEN_DISCLOSURE_ATTEMPTED":
        return "Assistant attempted to disclose sensitive token material."
    if event_type == "TOKEN_DISCLOSED":
        return "Sensitive token was exposed during the session."
    if event_type == "ATTACK_EMAIL_SENT":
        return "Attack email was delivered to the runtime inbox."
    return None


def _compute_evidence_strength(
    *, default_priority: EvidencePriority, evidence_type: EvidenceType
) -> EvidencePriority:
    if evidence_type == "exploit_outcome":
        return "high"
    if evidence_type == "exploit_step" and default_priority == "low":
        return "medium"
    if evidence_type == "system_context" and default_priority == "high":
        return "medium"
    return default_priority


def project_report_evidence(
    rows: Sequence[SessionReportEvidenceRow],
) -> tuple[ReportEvidenceProjection, ...]:
    projections: list[ReportEvidenceProjection] = []
    for row in rows:
        objective_mapping = tuple(
            ReportObjectiveMapping(
                objective_key=key,
                label=_OBJECTIVE_METADATA.get(key, (key, "unmapped_objective"))[0],
                rubric_target=_OBJECTIVE_METADATA.get(key, (key, "unmapped_objective"))[
                    1
                ],
            )
            for key in row.objective_keys
        )
        projections.append(
            ReportEvidenceProjection(
                event_id=row.event_id,
                position=row.position,
                title=row.title,
                description=row.description,
                details=row.details,
                occurred_at=row.occurred_at,
                trace_version=row.trace_version,
                event_index=row.event_index,
                evidence_type=row.evidence_type,
                objective_keys=row.objective_keys,
                why_it_matters=row.why_it_matters,
                default_priority=row.default_priority,
                citation_label=f"E{row.position + 1}",
                objective_mapping=objective_mapping,
                evidence_strength=_compute_evidence_strength(
                    default_priority=row.default_priority,
                    evidence_type=row.evidence_type,
                ),
                student_note=row.student_note,
            )
        )
    return tuple(projections)


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
    trace_events_by_id = {event.event_id: event for event in trace_events}

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

        trace_event = trace_events_by_id.get(item.event_id)
        if trace_event is None:
            raise InvalidSessionReportEvidenceError(
                message="event_id does not belong to session trace",
                details={
                    "session_id": str(session_id),
                    "event_id": str(item.event_id),
                },
            )
        event_type = trace_event.event_type
        (
            report_selectable,
            evidence_type,
            objective_keys,
            why_it_matters,
            default_priority,
        ) = _trace_evidence_annotation(event_type=event_type)

        if enforce_selectable_only and (
            event_type not in _REPORT_SELECTABLE_TRACE_EVENT_TYPES
            or not report_selectable
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
                title=_title_from_event_type(event_type),
                description=_description_from_event_type(event_type),
                details=dict(trace_event.payload),
                occurred_at=trace_event.occurred_at,
                trace_version=trace_event.trace_version,
                event_index=trace_event.event_index,
                evidence_type=evidence_type,
                objective_keys=objective_keys,
                why_it_matters=why_it_matters,
                default_priority=default_priority,
                student_note=item.student_note,
            )
        )

    repo.replace_report_evidence_for_session(
        session_id=session_id,
        items=normalized_items,
    )
    return tuple(normalized_items)


def import_selected_evidence(
    *,
    session_id: UUID,
    principal: PrincipalContext,
    repo: SessionReportEvidenceRepositoryPort,
    event_ids_override: Sequence[UUID] | None,
) -> tuple[SessionReportEvidenceRow, ...]:
    _require_owner_or_admin(session_id=session_id, principal=principal, repo=repo)
    selected_rows = repo.list_report_evidence_for_session(session_id=session_id)

    if event_ids_override is None:
        return tuple(selected_rows)

    row_by_event_id = {row.event_id: row for row in selected_rows}
    seen: set[UUID] = set()
    ordered_rows: list[SessionReportEvidenceRow] = []
    for event_id in event_ids_override:
        if event_id in seen:
            raise InvalidSessionReportEvidenceError(
                message="duplicate event_id in import-selected-evidence payload",
                details={
                    "session_id": str(session_id),
                    "event_id": str(event_id),
                },
            )
        seen.add(event_id)
        row = row_by_event_id.get(event_id)
        if row is None:
            raise InvalidSessionReportEvidenceError(
                message="event_id is not selected for this session",
                details={
                    "session_id": str(session_id),
                    "event_id": str(event_id),
                },
            )
        ordered_rows.append(row)
    return tuple(ordered_rows)
