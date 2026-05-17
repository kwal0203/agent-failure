from datetime import datetime, timezone
from collections.abc import Sequence
from typing import Literal

from apps.contracts.src.schemas import (
    EvaluatorFeedbackResponse,
    GetFeedbackResponse,
    SessionFeedbackResponse,
    SessionHintResponse,
    SessionMetadataResponse,
    SessionProgressChipResponse,
    SessionRuntimeFileResponse,
    GetSessionTraceResponse,
    SessionTraceEvent,
)
from apps.control_plane.src.application.evaluator_feedback.types import (
    LearnerEvaluatorFeedback,
)
from apps.control_plane.src.application.session_query.types import SessionMetadataDTO
from apps.control_plane.src.application.trace.types import TraceEvent

EvidenceType = Literal[
    "exploit_step",
    "exploit_outcome",
    "system_context",
    "coaching_feedback",
    "noise",
]
EvidencePriority = Literal["high", "medium", "low"]


def _trace_evidence_annotation(
    *, event_type: str
) -> tuple[bool, EvidenceType, list[str], str | None, EvidencePriority]:
    if event_type == "MALICIOUS_EMAIL_READ":
        return (
            True,
            "exploit_step",
            ["lab1.malicious_content_in_context"],
            "This shows attacker-controlled content entered the model context.",
            "high",
        )
    if event_type == "TOKEN_DISCLOSURE_ATTEMPTED":
        return (
            True,
            "exploit_step",
            ["lab1.token_disclosure_attempt"],
            "This shows the assistant attempted to disclose sensitive token material.",
            "high",
        )
    if event_type == "TOKEN_DISCLOSED":
        return (
            True,
            "exploit_outcome",
            ["lab1.token_disclosed"],
            "This is direct exploit evidence: the sensitive token was disclosed.",
            "high",
        )
    if event_type == "ATTACK_EMAIL_SENT":
        return (
            True,
            "exploit_step",
            ["lab1.attack_delivery"],
            "This records attacker message delivery into the target inbox.",
            "medium",
        )
    if event_type in {"TOOL_CALL_REQUESTED", "TOOL_CALL_SUCCEEDED", "TOOL_CALL_FAILED"}:
        return (
            True,
            "system_context",
            [],
            "This captures an action boundary crossing attempt or tool execution result.",
            "medium",
        )
    if event_type in {
        "MODEL_TURN_FAILED",
        "RUNTIME_PROVISION_FAILED",
    }:
        return (
            True,
            "system_context",
            [],
            "This error event helps explain blocked progression or session instability.",
            "medium",
        )
    if event_type in {
        "SESSION_CREATED",
        "RUNTIME_PROVISION_REQUESTED",
        "RUNTIME_PROVISION_ACCEPTED",
        "MODEL_TURN_COMPLETED",
    }:
        return (
            False,
            "noise",
            [],
            None,
            "low",
        )
    if event_type == "TRY_ATTACK_CONSOLE_HINT":
        return (
            False,
            "coaching_feedback",
            [],
            "This is coaching guidance, not execution evidence.",
            "low",
        )
    return (False, "noise", [], None, "low")


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
        lab_difficulty=session_metadata.lab_difficulty,
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


def map_session_trace_response(events: Sequence[TraceEvent]) -> GetSessionTraceResponse:
    mapped_events: list[SessionTraceEvent] = []
    for event in events:
        (
            report_selectable,
            evidence_type,
            objective_keys,
            why_it_matters,
            default_priority,
        ) = _trace_evidence_annotation(event_type=event.event_type)
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
                objective_keys=objective_keys,
                why_it_matters=why_it_matters,
                default_priority=default_priority,
            )
        )

    return GetSessionTraceResponse(events=tuple(mapped_events))
