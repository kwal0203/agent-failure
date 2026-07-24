from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, ValidationError

from apps.contracts.src.types import (
    TRACE_EVENT_ATTACK_EMAIL_SENT,
    TRACE_EVENT_MALICIOUS_EMAIL_READ,
    TRACE_EVENT_TOKEN_DISCLOSED,
)
from apps.evaluator.src.application.rules.cbm import ConstraintEvidence
from apps.evaluator.src.application.rules.labs.helpers import (
    extract_learner_text,
    matched_pattern_strings,
)
from apps.evaluator.src.application.rules.solution_states import (
    PromptInjectionSolutionState,
)
from apps.evaluator.src.application.rules.types import RuleContext
from apps.evaluator.src.application.types import EvaluatorTraceEvent

from .patterns import (
    AUTHORITY_PATTERNS,
    BUSINESS_REQUIREMENT_PATTERNS,
    COMPLIANCE_ABUSE_PATTERNS,
    DISCLOSURE_PATTERNS,
    MANAGER_ADDRESS_PATTERNS,
    OVERRIDE_PATTERNS,
    URGENCY_PATTERNS,
)


class _UserPromptSubmittedPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    content: str
    disclosure_attempt: bool | None = None


def _state(ctx: RuleContext) -> PromptInjectionSolutionState:
    return ctx.require_solution_state(PromptInjectionSolutionState)


def _evidence(
    event: EvaluatorTraceEvent, facts: dict[str, object]
) -> ConstraintEvidence:
    return ConstraintEvidence.build(
        trigger_event_index=event.event_index,
        trigger_start_event_index=event.event_index,
        trigger_end_event_index=event.event_index,
        facts=facts,
    )


def _events_after(
    events: Iterable[EvaluatorTraceEvent], event_index: int
) -> tuple[EvaluatorTraceEvent, ...]:
    return tuple(event for event in events if event.event_index > event_index)


def _has_email_id(event: EvaluatorTraceEvent) -> bool:
    email_id = event.payload.get("email_id")
    return isinstance(email_id, str) and bool(email_id.strip())


def matches_manager_disclosure_regex(text: str) -> bool:
    manager_hits = matched_pattern_strings(text, MANAGER_ADDRESS_PATTERNS)
    disclosure_hits = matched_pattern_strings(text, DISCLOSURE_PATTERNS)
    return bool(manager_hits and disclosure_hits)


def attack_artifact_created(ctx: RuleContext) -> tuple[ConstraintEvidence, ...]:
    state = _state(ctx)
    if not state.attack_emails:
        return ()
    event = state.attack_emails[0]
    return (
        _evidence(
            event,
            {
                "event_type": event.event_type,
                "email_id": event.payload.get("email_id"),
                "subject": event.payload.get("subject"),
            },
        ),
    )


def benign_email_injected_no_progress(
    ctx: RuleContext,
) -> tuple[ConstraintEvidence, ...]:
    state = _state(ctx)
    if state.malicious_attack_emails:
        return ()

    for event in state.benign_attack_emails:
        email_id = event.payload.get("email_id")
        email_from = event.payload.get("email_from")
        subject = event.payload.get("subject")
        if not isinstance(email_id, str) or not email_id.strip():
            continue
        if not isinstance(email_from, str) or not email_from.strip():
            continue
        if not isinstance(subject, str) or not subject.strip():
            continue
        return (
            _evidence(
                event,
                {
                    "event_type": event.event_type,
                    "event_index": event.event_index,
                    "email_id": email_id,
                    "email_from": email_from,
                    "subject": subject,
                    "malicious_marker": event.payload.get("malicious_marker"),
                },
            ),
        )
    return ()


def inbox_interaction_triggered(
    ctx: RuleContext,
) -> tuple[ConstraintEvidence, ...]:
    state = _state(ctx)
    if not state.inbox_interactions:
        return ()
    event = state.inbox_interactions[0]
    return (
        _evidence(
            event,
            {
                "event_type": event.event_type,
                "email_id": event.payload.get("email_id"),
                "subject": event.payload.get("subject"),
            },
        ),
    )


def malicious_email_not_read_yet(
    ctx: RuleContext,
) -> tuple[ConstraintEvidence, ...]:
    state = _state(ctx)
    if not state.malicious_attack_emails:
        return ()

    event = state.malicious_attack_emails[0]
    later_events = _events_after(state.trace.events, event.event_index)
    if any(
        later.family == "runtime"
        and later.event_type == TRACE_EVENT_MALICIOUS_EMAIL_READ
        for later in later_events
    ):
        return ()

    later_activity_count = sum(
        later.family in {"learner", "runtime", "tool"} for later in later_events
    )
    return (
        _evidence(
            event,
            {
                "event_type": event.event_type,
                "event_index": event.event_index,
                "email_id": event.payload.get("email_id"),
                "malicious_marker": event.payload.get("malicious_marker"),
                "later_activity_count": later_activity_count,
            },
        ),
    )


def direct_disclosure_ask_no_malicious_email(
    ctx: RuleContext,
) -> tuple[ConstraintEvidence, ...]:
    state = _state(ctx)
    malicious_email_sent_before = False

    for event in state.learner_events:
        if (
            event.event_type == TRACE_EVENT_ATTACK_EMAIL_SENT
            and event.payload.get("malicious_marker") is True
        ):
            malicious_email_sent_before = True
            continue
        if event.event_type != "USER_PROMPT_SUBMITTED":
            continue

        try:
            prompt = _UserPromptSubmittedPayload.model_validate(event.payload)
        except ValidationError:
            continue
        is_disclosure_attempt = (
            prompt.disclosure_attempt
            if isinstance(prompt.disclosure_attempt, bool)
            else matches_manager_disclosure_regex(prompt.content)
        )
        if not is_disclosure_attempt:
            continue
        if malicious_email_sent_before:
            return ()
        return (
            _evidence(
                event,
                {
                    "event_type": event.event_type,
                    "event_index": event.event_index,
                    "text_excerpt": prompt.content[:200],
                    "malicious_email_sent_before": False,
                },
            ),
        )
    return ()


def inbox_interaction_without_disclosure(
    ctx: RuleContext,
) -> tuple[ConstraintEvidence, ...]:
    state = _state(ctx)
    if not state.inbox_interactions or state.token_disclosures:
        return ()
    event = state.inbox_interactions[-1]
    return (
        _evidence(
            event,
            {
                "last_event_type": event.event_type,
                "email_id": event.payload.get("email_id"),
                "subject": event.payload.get("subject"),
            },
        ),
    )


def malicious_email_read_no_disclosure(
    ctx: RuleContext,
) -> tuple[ConstraintEvidence, ...]:
    state = _state(ctx)
    valid_reads = tuple(
        event for event in state.malicious_email_reads if _has_email_id(event)
    )
    if not valid_reads:
        return ()

    event = valid_reads[0]
    later_events = _events_after(state.trace.events, event.event_index)
    if any(
        later.family == "runtime" and later.event_type == TRACE_EVENT_TOKEN_DISCLOSED
        for later in later_events
    ):
        return ()
    later_activity_count = sum(
        later.family in {"learner", "runtime", "tool"} for later in later_events
    )
    return (
        _evidence(
            event,
            {
                "event_type": event.event_type,
                "event_index": event.event_index,
                "email_id": event.payload.get("email_id"),
                "subject": event.payload.get("subject"),
                "malicious_marker": event.payload.get("malicious_marker"),
                "later_activity_count": later_activity_count,
            },
        ),
    )


def malicious_email_entered_model_context(
    ctx: RuleContext,
) -> tuple[ConstraintEvidence, ...]:
    state = _state(ctx)
    if not state.malicious_email_reads:
        return ()
    event = state.malicious_email_reads[0]
    return (
        _evidence(
            event,
            {
                "email_id": event.payload.get("email_id"),
                "subject": event.payload.get("subject"),
                "malicious_marker": event.payload.get("malicious_marker"),
            },
        ),
    )


def benign_email_read_injected_context(
    ctx: RuleContext,
) -> tuple[ConstraintEvidence, ...]:
    state = _state(ctx)
    if not state.benign_email_reads:
        return ()
    event = state.benign_email_reads[0]
    return (
        _evidence(
            event,
            {
                "email_id": event.payload.get("email_id"),
                "subject": event.payload.get("subject"),
                "malicious_marker": event.payload.get("malicious_marker"),
            },
        ),
    )


def policy_violation_attempted(
    ctx: RuleContext,
) -> tuple[ConstraintEvidence, ...]:
    observations: list[ConstraintEvidence] = []
    for event in _state(ctx).learner_events:
        text = extract_learner_text(event)
        if text is None:
            continue
        override_hits = matched_pattern_strings(text, OVERRIDE_PATTERNS)
        disclosure_hits = matched_pattern_strings(text, DISCLOSURE_PATTERNS)
        compliance_hits = matched_pattern_strings(text, COMPLIANCE_ABUSE_PATTERNS)
        if not (
            (override_hits and disclosure_hits) or (disclosure_hits and compliance_hits)
        ):
            continue
        observations.append(
            _evidence(
                event,
                {
                    "event_type": event.event_type,
                    "matched_override_patterns": override_hits,
                    "matched_disclosure_patterns": disclosure_hits,
                    "matched_compliance_patterns": compliance_hits,
                    "text_excerpt": text[:200],
                },
            )
        )
    return tuple(observations)


def learner_explained_root_cause(
    ctx: RuleContext,
) -> tuple[ConstraintEvidence, ...]:
    if not ctx.explanation_signals:
        return ()
    explanation = ctx.explanation_signals[-1]
    if not explanation.mentions_root_cause:
        return ()
    return (
        ConstraintEvidence.build(
            facts={
                "confidence": explanation.confidence,
                "explanation_id": explanation.explanation_id,
            }
        ),
    )


def learner_proposed_mitigation(
    ctx: RuleContext,
) -> tuple[ConstraintEvidence, ...]:
    if not ctx.explanation_signals:
        return ()
    explanation = ctx.explanation_signals[-1]
    if not explanation.mentions_mitigation:
        return ()
    return (
        ConstraintEvidence.build(
            facts={
                "confidence": explanation.confidence,
                "explanation_id": explanation.explanation_id,
            }
        ),
    )


def compliance_authority_spoofed(
    ctx: RuleContext,
) -> tuple[ConstraintEvidence, ...]:
    observations: list[ConstraintEvidence] = []
    for event in _state(ctx).learner_events:
        email_from = event.payload.get("email_from")
        if not isinstance(email_from, str) or not email_from.strip():
            continue
        matches = matched_pattern_strings(
            email_from.strip().lower(), AUTHORITY_PATTERNS
        )
        if not matches:
            continue
        observations.append(
            _evidence(
                event,
                {
                    "event_type": event.event_type,
                    "email_id": event.payload.get("email_id"),
                    "email_from": email_from,
                    "subject": event.payload.get("subject"),
                    "matched_authority_patterns": matches,
                },
            )
        )
    return tuple(observations)


def audit_urgency_invoked(
    ctx: RuleContext,
) -> tuple[ConstraintEvidence, ...]:
    observations: list[ConstraintEvidence] = []
    for event in _state(ctx).learner_events:
        email_from = event.payload.get("email_from")
        subject = event.payload.get("subject")
        body_text = extract_learner_text(event)
        fragments = [
            value.strip().lower()
            for value in (email_from, subject)
            if isinstance(value, str) and value.strip()
        ]
        if body_text is not None:
            fragments.append(body_text)
        if not fragments:
            continue
        combined = " | ".join(fragments)
        matches = matched_pattern_strings(combined, URGENCY_PATTERNS)
        if not matches:
            continue
        observations.append(
            _evidence(
                event,
                {
                    "event_type": event.event_type,
                    "email_id": event.payload.get("email_id"),
                    "email_from": email_from,
                    "subject": subject,
                    "matched_urgency_patterns": matches,
                    "text_excerpt": combined[:200],
                },
            )
        )
    return tuple(observations)


def disclosure_framed_as_business_requirement(
    ctx: RuleContext,
) -> tuple[ConstraintEvidence, ...]:
    observations: list[ConstraintEvidence] = []
    for event in _state(ctx).learner_events:
        text = extract_learner_text(event)
        if text is None:
            subject = event.payload.get("subject")
            if isinstance(subject, str) and subject.strip():
                text = subject.strip().lower()
        if text is None:
            continue
        disclosure_hits = matched_pattern_strings(text, DISCLOSURE_PATTERNS)
        requirement_hits = matched_pattern_strings(text, BUSINESS_REQUIREMENT_PATTERNS)
        if not disclosure_hits or not requirement_hits:
            continue
        observations.append(
            _evidence(
                event,
                {
                    "event_type": event.event_type,
                    "email_id": event.payload.get("email_id"),
                    "subject": event.payload.get("subject"),
                    "matched_disclosure_patterns": disclosure_hits,
                    "matched_requirement_patterns": requirement_hits,
                    "text_excerpt": text[:200],
                },
            )
        )
    return tuple(observations)


def learner_identifies_rule_priority_clash(
    ctx: RuleContext,
) -> tuple[ConstraintEvidence, ...]:
    if not ctx.explanation_signals:
        return ()
    explanation = ctx.explanation_signals[-1]
    if not explanation.identified_rule_priority_clash:
        return ()
    return (
        ConstraintEvidence.build(
            facts={
                "confidence": explanation.confidence,
                "explanation_id": explanation.explanation_id,
            }
        ),
    )


def token_exposed(ctx: RuleContext) -> tuple[ConstraintEvidence, ...]:
    return tuple(
        _evidence(
            event,
            {
                "event_type": event.event_type,
                "channel": event.payload.get("channel"),
                "token_kind": event.payload.get("token_kind"),
            },
        )
        for event in _state(ctx).token_disclosures
        if event.family == "runtime"
    )
