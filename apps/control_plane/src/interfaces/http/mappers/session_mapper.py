from datetime import datetime, timezone
from collections.abc import Sequence

from apps.contracts.src.schemas import (
    EvaluatorFeedbackResponse,
    GetFeedbackResponse,
    GetSessionsResponse,
    SessionFeedbackResponse,
    SessionHintResponse,
    SessionMetadataResponse,
    SessionSummaryResponse,
    SessionProgressChipResponse,
    SessionRuntimeFileResponse,
    GetSessionTraceResponse,
    SessionTraceEvent,
    GetSessionReportEvidenceResponse,
    GetSessionReportDraftResponse,
    ObjectiveMappingItem,
    ReportEvidenceItem,
    ReportDraftSections,
)
from apps.control_plane.src.application.evaluator_feedback.types import (
    LearnerEvaluatorFeedback,
)
from apps.control_plane.src.application.session_query.types import (
    SessionMetadataDTO,
    SessionSummaryDTO,
)
from apps.control_plane.src.application.trace.types import TraceEvent
from apps.control_plane.src.application.session_report_evidence.types import (
    ReportEvidenceProjection,
    SessionReportDraftSections as AppSessionReportDraftSections,
    SessionReportEvidenceItemInput,
    SessionReportEvidenceRow,
)
from apps.control_plane.src.application.session_report_evidence.service import (
    project_report_evidence,
    trace_evidence_annotation,
)


def map_session_metadata_response(
    *,
    session_metadata: SessionMetadataDTO,
    provisioning_stalled: bool,
    runtime_files: list[SessionRuntimeFileResponse],
) -> SessionMetadataResponse:
    progress_chips = [
        SessionProgressChipResponse(
            objective_key=item.objective_key,
            label=item.label,
            status=item.status,
            completed_at=item.completed_at,
            updated_at=item.updated_at,
        )
        for item in session_metadata.progress_chips
    ]

    hints = [
        SessionHintResponse(
            hint_key=item.hint_key,
            text=item.text,
            sort_order=item.sort_order,
            status=item.status,
            unlock_at=item.unlock_at,
            unlocked_at=item.unlocked_at,
            seen_at=item.seen_at,
        )
        for item in session_metadata.hints
    ]

    feedback = [
        SessionFeedbackResponse(
            id=item.id,
            feedback_key=item.feedback_key,
            reason_code=item.reason_code,
            message=item.message,
            severity=item.severity,
            trigger_event_index=item.trigger_event_index,
            created_at=item.created_at,
            seen_at=item.seen_at,
        )
        for item in session_metadata.feedback
    ]

    return SessionMetadataResponse(
        id=session_metadata.id,
        lab_id=session_metadata.lab_id,
        lab_version_id=session_metadata.lab_version_id,
        state=session_metadata.state,
        runtime_substate=session_metadata.runtime_substate,
        resume_mode=session_metadata.resume_mode,
        last_transition_reason=session_metadata.last_transition_reason,
        interactive=session_metadata.interactive,
        created_at=session_metadata.created_at,
        started_at=session_metadata.started_at,
        ended_at=session_metadata.ended_at,
        completion_status=session_metadata.completion_status,
        completed_at=session_metadata.completed_at,
        completion_reason_code=session_metadata.completion_reason_code,
        provisioning_stalled=provisioning_stalled,
        provisioning_stall_reason_code="SESSION_PROVISIONING_STALLED"
        if provisioning_stalled
        else None,
        progress_chips=progress_chips,
        hints=hints,
        unread_hint_count=session_metadata.unread_hint_count,
        feedback_items=feedback,
        feedback=feedback,
        unread_feedback_count=session_metadata.unread_feedback_count,
        runtime_files=runtime_files,
    )


def build_runtime_file_response(
    *, path: str, content: str
) -> SessionRuntimeFileResponse:
    return SessionRuntimeFileResponse(
        path=path,
        content=content,
        updated_at=datetime.now(timezone.utc),
    )


def map_evaluator_feedback_response(
    feedback: Sequence[LearnerEvaluatorFeedback],
) -> GetFeedbackResponse:
    return GetFeedbackResponse(
        feedback=tuple(
            EvaluatorFeedbackResponse(
                status=item.status,
                reason_code=item.reason_code,
                evidence_snippet=item.evidence_snippet,
            )
            for item in feedback
        )
    )


def map_sessions_response(items: Sequence[SessionSummaryDTO]) -> GetSessionsResponse:
    return GetSessionsResponse(
        sessions=tuple(
            SessionSummaryResponse(
                session_id=item.session_id,
                lab_id=item.lab_id,
                created_at=item.created_at,
                state=item.state,
                completion_status=item.completion_status,
            )
            for item in items
        )
    )


def map_session_trace_response(events: Sequence[TraceEvent]) -> GetSessionTraceResponse:
    mapped_events: list[SessionTraceEvent] = []
    for event in events:
        (
            report_selectable,
            evidence_type,
            objective_keys,
            why_it_matters,
            default_priority,
        ) = trace_evidence_annotation(event_type=event.event_type)
        mapped_events.append(
            SessionTraceEvent(
                id=event.event_id,
                event_index=event.event_index,
                family=event.family,
                event_type=event.event_type,
                source=event.source,
                occurred_at=event.occurred_at,
                payload=dict(event.payload),
                report_selectable=report_selectable,
                evidence_type=evidence_type,
                objective_keys=list(objective_keys),
                why_it_matters=why_it_matters,
                default_priority=default_priority,
            )
        )

    return GetSessionTraceResponse(events=tuple(mapped_events))


def map_session_report_evidence_response(
    rows: Sequence[SessionReportEvidenceRow],
) -> GetSessionReportEvidenceResponse:
    projections = project_report_evidence(rows)
    return map_report_evidence_projection_response(projections)


def map_report_evidence_projection_response(
    items: Sequence[ReportEvidenceProjection],
) -> GetSessionReportEvidenceResponse:
    return GetSessionReportEvidenceResponse(
        items=tuple(
            ReportEvidenceItem(
                event_id=item.event_id,
                position=item.position,
                title=item.title,
                description=item.description,
                details=item.details,
                occurred_at=item.occurred_at,
                trace_version=item.trace_version,
                event_index=item.event_index,
                evidence_type=item.evidence_type,
                objective_keys=item.objective_keys,
                why_it_matters=item.why_it_matters,
                default_priority=item.default_priority,
                citation_label=item.citation_label,
                objective_mapping=tuple(
                    ObjectiveMappingItem(
                        objective_key=mapped.objective_key,
                        label=mapped.label,
                        rubric_target=mapped.rubric_target,
                    )
                    for mapped in item.objective_mapping
                ),
                evidence_strength=item.evidence_strength,
                student_note=item.student_note,
                report_section=item.report_section,
                section_position=item.section_position,
            )
            for item in items
        )
    )


def map_report_evidence_items_to_inputs(
    items: Sequence[ReportEvidenceItem],
) -> tuple[SessionReportEvidenceItemInput, ...]:
    return tuple(
        SessionReportEvidenceItemInput(
            event_id=item.event_id,
            position=item.position,
            title=item.title,
            description=item.description,
            details=item.details,
            occurred_at=item.occurred_at,
            trace_version=item.trace_version,
            event_index=item.event_index,
            evidence_type=item.evidence_type,
            objective_keys=tuple(item.objective_keys),
            why_it_matters=item.why_it_matters,
            default_priority=item.default_priority,
            student_note=item.student_note,
            report_section=item.report_section,
            section_position=item.section_position,
        )
        for item in items
    )


def map_report_draft_response(
    *,
    sections: AppSessionReportDraftSections | ReportDraftSections,
    rows: Sequence[SessionReportEvidenceRow],
) -> GetSessionReportDraftResponse:
    mapped_sections = (
        sections
        if isinstance(sections, ReportDraftSections)
        else ReportDraftSections(
            executive_summary=sections.executive_summary,
            threat_model=sections.threat_model,
            methodology=sections.methodology,
            evidence_and_results=sections.evidence_and_results,
            mitigations=sections.mitigations,
        )
    )
    return GetSessionReportDraftResponse(
        sections=mapped_sections,
        items=map_session_report_evidence_response(rows).items,
    )
