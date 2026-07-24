from uuid import UUID

from apps.evaluator.src.application.types import EvaluatorFinding, EvaluatorTraceEvent
from apps.evaluator.src.application.rules.types import RuleBundle, RuleFn, RuleContext
from apps.evaluator.src.application.rules.contract import (
    REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS,
    REASON_CODE_PI_BENIGN_EMAIL_READ_INJECTED_CONTEXT,
    REASON_CODE_PI_DIRECT_DISCLOSURE_ASK_NO_MALICIOUS_EMAIL,
    REASON_CODE_PI_MALICIOUS_ARTIFACT_ENTERED_CONTEXT,
    REASON_CODE_PI_MALICIOUS_EMAIL_READ_NO_DISCLOSURE,
    REASON_CODE_PI_MALICIOUS_EMAIL_NOT_READ_YET,
    RULE_ID_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS,
    RULE_ID_PI_BENIGN_EMAIL_READ_INJECTED_CONTEXT,
    RULE_ID_PI_DIRECT_DISCLOSURE_ASK_NO_MALICIOUS_EMAIL,
    RULE_ID_PI_MALICIOUS_EMAIL_READ_NO_DISCLOSURE,
    RULE_ID_PI_MALICIOUS_EMAIL_NOT_READ_YET,
)

from .helpers import extract_learner_text, matched_pattern_strings

from pydantic import BaseModel, ConfigDict, ValidationError

import re

from apps.contracts.src.lab_secrets import (
    LAB1_PROTECTED_SECRET_LABEL,
    LAB1_PROTECTED_SECRET_VALUE,
)
from apps.contracts.src.types import (
    TRACE_EVENT_ATTACK_EMAIL_SENT,
    TRACE_EVENT_MALICIOUS_EMAIL_READ,
    TRACE_EVENT_TOKEN_DISCLOSED,
    TRACE_EVENT_TOOL_CALL_REQUESTED,
    TRACE_EVENT_TOOL_CALL_SUCCEEDED,
)


_OVERRIDE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"\bignore\s+(all\s+)?(previous|prior|earlier)\s+(instructions?|rules?|prompts?)\b"
    ),
    re.compile(r"\bdisregard\s+(the\s+)?(above|earlier|prior)\b"),
    re.compile(r"\boverride\s+(security|policy|guardrails?)\b"),
)

_DISCLOSURE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(reveal|disclose|print|output|expose|show)\b", re.IGNORECASE),
    re.compile(
        r"\b(system[_\s-]?token|token|secret|internal\s+config(uration)?)\b",
        re.IGNORECASE,
    ),
    re.compile(re.escape(LAB1_PROTECTED_SECRET_LABEL), re.IGNORECASE),
    re.compile(re.escape(LAB1_PROTECTED_SECRET_VALUE), re.IGNORECASE),
)

_COMPLIANCE_ABUSE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b(compliance|audit|mandatory\s+procedure|urgent\s+directive)\b"),
)
_MANAGER_ADDRESS_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bmanagers?\s+(?:home\s+)?address\b", re.IGNORECASE),
    re.compile(r"\bmanager's\s+(?:home\s+)?address\b", re.IGNORECASE),
    re.compile(r"\bhome\s+address\b", re.IGNORECASE),
    re.compile(r"\bwhere\b.*\bmanager\b.*\blive\b", re.IGNORECASE),
)


def matches_manager_disclosure_regex(text: str) -> bool:
    manager_hits = matched_pattern_strings(text, _MANAGER_ADDRESS_PATTERNS)
    disclosure_hits = matched_pattern_strings(text, _DISCLOSURE_PATTERNS)
    return bool(manager_hits and disclosure_hits)


class _UserPromptSubmittedPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    content: str
    disclosure_attempt: bool | None = None


def _is_inbox_interaction_event(event: EvaluatorTraceEvent) -> bool:
    if (
        event.family == "runtime"
        and event.event_type == TRACE_EVENT_MALICIOUS_EMAIL_READ
    ):
        return True

    if event.family != "tool":
        return False
    if event.event_type not in {
        TRACE_EVENT_TOOL_CALL_REQUESTED,
        TRACE_EVENT_TOOL_CALL_SUCCEEDED,
    }:
        return False
    tool_name = event.payload.get("tool_name")
    return isinstance(tool_name, str) and tool_name in {"list_inbox", "read_email"}


def _malicious_email_sent(ctx: RuleContext) -> tuple[EvaluatorFinding, ...]:
    """
    Progress observation:
        Learner created an attack artifact by sending an email through the
        attacker console. Separate rules classify whether its content is
        malicious and whether it advances the exploit.
    """

    for event in ctx.events:
        if (
            event.event_type == TRACE_EVENT_ATTACK_EMAIL_SENT
            and event.family == "learner"
        ):
            return (
                EvaluatorFinding(
                    result_type="partial_success",
                    code="pi.attack_artifact_created",
                    trigger_event_index=event.event_index,
                    trigger_start_event_index=event.event_index,
                    trigger_end_event_index=event.event_index,
                    feedback_level="info",
                    reason_code="PI_ATTACK_ARTIFACT_CREATED",
                    feedback_payload={
                        "event_type": event.event_type,
                        "email_id": event.payload.get("email_id"),
                        "subject": event.payload.get("subject"),
                    },
                ),
            )

    return ()


def _benign_email_injected_no_progress(
    ctx: RuleContext,
) -> tuple[EvaluatorFinding, ...]:
    benign_event: EvaluatorTraceEvent | None = None

    for event in ctx.events:
        if (
            event.family != "learner"
            or event.event_type != TRACE_EVENT_ATTACK_EMAIL_SENT
        ):
            continue

        marker = event.payload.get("malicious_marker")
        if marker is True:
            return ()
        if marker is False and benign_event is None:
            email_id = event.payload.get("email_id")
            email_from = event.payload.get("email_from")
            subject = event.payload.get("subject")
            if not isinstance(email_id, str) or not email_id.strip():
                continue
            if not isinstance(email_from, str) or not email_from.strip():
                continue
            if not isinstance(subject, str) or not subject.strip():
                continue
            benign_event = event

    if benign_event is None:
        return ()

    payload = benign_event.payload
    return (
        EvaluatorFinding(
            result_type="no_effect",
            code=RULE_ID_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS,
            trigger_event_index=benign_event.event_index,
            trigger_start_event_index=benign_event.event_index,
            trigger_end_event_index=benign_event.event_index,
            feedback_level="info",
            reason_code=REASON_CODE_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS,
            feedback_payload={
                "event_type": benign_event.event_type,
                "event_index": benign_event.event_index,
                "email_id": payload.get("email_id"),
                "email_from": payload.get("email_from"),
                "subject": payload.get("subject"),
                "malicious_marker": payload.get("malicious_marker"),
            },
        ),
    )


def _inbox_interaction_triggered(ctx: RuleContext) -> tuple[EvaluatorFinding, ...]:
    """
    Educational constraint:
        G2a. Learner triggered inbox processing
        Satisfied if learner causes the assistant to list or read emails.
    """

    for event in ctx.events:
        if _is_inbox_interaction_event(event):
            return (
                EvaluatorFinding(
                    result_type="partial_success",
                    code="pi.inbox_interaction_triggered",
                    trigger_event_index=event.event_index,
                    trigger_start_event_index=event.event_index,
                    trigger_end_event_index=event.event_index,
                    feedback_level="info",
                    reason_code="PI_INBOX_INTERACTION_TRIGGERED",
                    feedback_payload={
                        "event_type": event.event_type,
                        "email_id": event.payload.get("email_id"),
                        "subject": event.payload.get("subject"),
                    },
                ),
            )

    return ()


def _malicious_email_not_read_yet(ctx: RuleContext) -> tuple[EvaluatorFinding, ...]:
    malicious_attack_event: EvaluatorTraceEvent | None = None
    malicious_read_seen = False
    later_activity_count = 0

    for event in ctx.events:
        if (
            malicious_attack_event is None
            and event.family == "learner"
            and event.event_type == TRACE_EVENT_ATTACK_EMAIL_SENT
            and event.payload.get("malicious_marker") is True
        ):
            email_id = event.payload.get("email_id")
            if not isinstance(email_id, str) or not email_id.strip():
                continue
            malicious_attack_event = event
            continue

        if malicious_attack_event is None:
            continue
        if event.event_index <= malicious_attack_event.event_index:
            continue

        if event.family in {"learner", "runtime", "tool"}:
            later_activity_count += 1
        if (
            event.family == "runtime"
            and event.event_type == TRACE_EVENT_MALICIOUS_EMAIL_READ
        ):
            malicious_read_seen = True

    if malicious_attack_event is None or malicious_read_seen:
        return ()

    return (
        EvaluatorFinding(
            result_type="no_effect",
            code=RULE_ID_PI_MALICIOUS_EMAIL_NOT_READ_YET,
            trigger_event_index=malicious_attack_event.event_index,
            trigger_start_event_index=malicious_attack_event.event_index,
            trigger_end_event_index=malicious_attack_event.event_index,
            feedback_level="info",
            reason_code=REASON_CODE_PI_MALICIOUS_EMAIL_NOT_READ_YET,
            feedback_payload={
                "event_type": malicious_attack_event.event_type,
                "event_index": malicious_attack_event.event_index,
                "email_id": malicious_attack_event.payload.get("email_id"),
                "malicious_marker": malicious_attack_event.payload.get(
                    "malicious_marker"
                ),
                "later_activity_count": later_activity_count,
            },
        ),
    )


def _direct_disclosure_ask_no_malicious_email(
    ctx: RuleContext,
) -> tuple[EvaluatorFinding, ...]:
    malicious_email_sent_before = False

    for event in ctx.events:
        if (
            event.family == "learner"
            and event.event_type == TRACE_EVENT_ATTACK_EMAIL_SENT
            and event.payload.get("malicious_marker") is True
        ):
            malicious_email_sent_before = True
            continue

        if event.family != "learner" or event.event_type != "USER_PROMPT_SUBMITTED":
            continue

        try:
            prompt_payload = _UserPromptSubmittedPayload.model_validate(event.payload)
        except ValidationError:
            continue
        text = prompt_payload.content

        if isinstance(prompt_payload.disclosure_attempt, bool):
            is_disclosure_attempt = prompt_payload.disclosure_attempt
        else:
            is_disclosure_attempt = matches_manager_disclosure_regex(text)

        if not is_disclosure_attempt:
            continue
        if malicious_email_sent_before:
            return ()

        return (
            EvaluatorFinding(
                result_type="no_effect",
                code=RULE_ID_PI_DIRECT_DISCLOSURE_ASK_NO_MALICIOUS_EMAIL,
                trigger_event_index=event.event_index,
                trigger_start_event_index=event.event_index,
                trigger_end_event_index=event.event_index,
                feedback_level="info",
                reason_code=REASON_CODE_PI_DIRECT_DISCLOSURE_ASK_NO_MALICIOUS_EMAIL,
                feedback_payload={
                    "event_type": event.event_type,
                    "event_index": event.event_index,
                    "text_excerpt": text[:200],
                    "malicious_email_sent_before": malicious_email_sent_before,
                },
            ),
        )

    return ()


def _inbox_interaction_without_disclosure(
    ctx: RuleContext,
) -> tuple[EvaluatorFinding, ...]:
    """
    Educational constraint:
        G2b. Learner triggered inbox processing
        Satisfied if learner causes the assistant to list or read emails.
    """

    inbox_interaction = False
    token_disclosed = False
    last_event: EvaluatorTraceEvent | None = None

    for event in ctx.events:
        if _is_inbox_interaction_event(event):
            inbox_interaction = True
            last_event = event
        elif event.event_type == TRACE_EVENT_TOKEN_DISCLOSED:
            token_disclosed = True

    if not inbox_interaction or token_disclosed or last_event is None:
        return ()

    return (
        EvaluatorFinding(
            result_type="no_effect",
            code="pi.inbox_interaction_without_disclosure",
            trigger_event_index=last_event.event_index,
            trigger_start_event_index=last_event.event_index,
            trigger_end_event_index=last_event.event_index,
            feedback_level="info",
            reason_code="PI_INBOX_INTERACTION_WITHOUT_DISCLOSURE",
            feedback_payload={
                "last_event_type": last_event.event_type,
                "email_id": last_event.payload.get("email_id"),
                "subject": last_event.payload.get("subject"),
            },
        ),
    )


def _malicious_email_read_no_disclosure(
    ctx: RuleContext,
) -> tuple[EvaluatorFinding, ...]:
    malicious_read_event: EvaluatorTraceEvent | None = None
    token_disclosed_after_read = False
    later_activity_count = 0

    for event in ctx.events:
        if (
            malicious_read_event is None
            and event.family == "runtime"
            and event.event_type == TRACE_EVENT_MALICIOUS_EMAIL_READ
            and event.payload.get("malicious_marker") is True
        ):
            email_id = event.payload.get("email_id")
            if not isinstance(email_id, str) or not email_id.strip():
                continue
            malicious_read_event = event
            continue

        if malicious_read_event is None:
            continue
        if event.event_index <= malicious_read_event.event_index:
            continue

        if event.family in {"learner", "runtime", "tool"}:
            later_activity_count += 1
        if (
            event.family == "runtime"
            and event.event_type == TRACE_EVENT_TOKEN_DISCLOSED
        ):
            token_disclosed_after_read = True

    if malicious_read_event is None or token_disclosed_after_read:
        return ()

    return (
        EvaluatorFinding(
            result_type="no_effect",
            code=RULE_ID_PI_MALICIOUS_EMAIL_READ_NO_DISCLOSURE,
            trigger_event_index=malicious_read_event.event_index,
            trigger_start_event_index=malicious_read_event.event_index,
            trigger_end_event_index=malicious_read_event.event_index,
            feedback_level="info",
            reason_code=REASON_CODE_PI_MALICIOUS_EMAIL_READ_NO_DISCLOSURE,
            feedback_payload={
                "event_type": malicious_read_event.event_type,
                "event_index": malicious_read_event.event_index,
                "email_id": malicious_read_event.payload.get("email_id"),
                "subject": malicious_read_event.payload.get("subject"),
                "malicious_marker": malicious_read_event.payload.get(
                    "malicious_marker"
                ),
                "later_activity_count": later_activity_count,
            },
        ),
    )


def _malicious_email_entered_model_context(
    ctx: RuleContext,
) -> tuple[EvaluatorFinding, ...]:
    """
    Educational constraint:
        G3. Malicious artifact entered model context
        Satisfied if the assistant reads the learner-crafted email.
    """

    for event in ctx.events:
        if (
            event.event_type == TRACE_EVENT_MALICIOUS_EMAIL_READ
            and event.family == "runtime"
            and event.payload.get("malicious_marker") is True
        ):
            return (
                EvaluatorFinding(
                    result_type="partial_success",
                    code="pi.malicious_artifact_entered_context",
                    trigger_event_index=event.event_index,
                    trigger_start_event_index=event.event_index,
                    trigger_end_event_index=event.event_index,
                    feedback_level="flag",
                    reason_code=REASON_CODE_PI_MALICIOUS_ARTIFACT_ENTERED_CONTEXT,
                    feedback_payload={
                        "email_id": event.payload.get("email_id"),
                        "subject": event.payload.get("subject"),
                        "malicious_marker": event.payload.get("malicious_marker"),
                    },
                ),
            )

    return ()


def _benign_email_read_injected_context(
    ctx: RuleContext,
) -> tuple[EvaluatorFinding, ...]:
    for event in ctx.events:
        if (
            event.event_type == TRACE_EVENT_MALICIOUS_EMAIL_READ
            and event.family == "runtime"
            and event.payload.get("malicious_marker") is False
        ):
            return (
                EvaluatorFinding(
                    result_type="no_effect",
                    code=RULE_ID_PI_BENIGN_EMAIL_READ_INJECTED_CONTEXT,
                    trigger_event_index=event.event_index,
                    trigger_start_event_index=event.event_index,
                    trigger_end_event_index=event.event_index,
                    feedback_level="info",
                    reason_code=REASON_CODE_PI_BENIGN_EMAIL_READ_INJECTED_CONTEXT,
                    feedback_payload={
                        "email_id": event.payload.get("email_id"),
                        "subject": event.payload.get("subject"),
                        "malicious_marker": event.payload.get("malicious_marker"),
                    },
                ),
            )

    return ()


def _learner_pursued_concrete_policy_violation(
    ctx: RuleContext,
) -> tuple[EvaluatorFinding, ...]:
    # This deterministic heuristic is deliberately conservative. Expand its
    # characterized patterns when new supported attack phrasing is introduced.
    """
    Educational constraint:
        G4. Learner pursued a concrete policy violation
        Satisfied if learner attempts to induce disclosure of protected information.
    """
    findings: list[EvaluatorFinding] = []

    for event in ctx.events:
        if event.family != "learner":
            continue

        text = extract_learner_text(event)
        if text is None:
            continue

        override_hits = matched_pattern_strings(text, _OVERRIDE_PATTERNS)
        disclosure_hits = matched_pattern_strings(text, _DISCLOSURE_PATTERNS)
        compliance_hits = matched_pattern_strings(text, _COMPLIANCE_ABUSE_PATTERNS)

        pursued_violation = (len(override_hits) > 0 and len(disclosure_hits) > 0) or (
            len(disclosure_hits) > 0 and len(compliance_hits) > 0
        )
        if not pursued_violation:
            continue

        findings.append(
            EvaluatorFinding(
                result_type="partial_success",
                code="pi.policy_violation_attempted",
                trigger_event_index=event.event_index,
                trigger_start_event_index=event.event_index,
                trigger_end_event_index=event.event_index,
                feedback_level="info",
                reason_code="PI_POLICY_VIOLATION_ATTEMPTED",
                feedback_payload={
                    "event_type": event.event_type,
                    "matched_override_patterns": override_hits,
                    "matched_disclosure_patterns": disclosure_hits,
                    "matched_compliance_patterns": compliance_hits,
                    "text_excerpt": text[:200],
                },
            )
        )

    return tuple(findings)


def _learner_explained_root_cause(ctx: RuleContext) -> tuple[EvaluatorFinding, ...]:
    """
    Educational constraint:
        G5. Learner explained root cause
        Satisfied if learner identifies that untrusted email content was treated as instructions or granted too much authority.
    """

    explanation_signals = ctx.explanation_signals
    if not explanation_signals:
        return ()

    final_explanation = explanation_signals[-1]
    if final_explanation.mentions_root_cause:
        return (
            EvaluatorFinding(
                result_type="partial_success",
                code="pi.explanation.mentioned_root_cause",
                trigger_event_index=None,
                trigger_end_event_index=None,
                trigger_start_event_index=None,
                feedback_level="info",
                reason_code="PI_EXPLANATION_MENTIONED_ROOT_CAUSE",
                feedback_payload={
                    "confidence": final_explanation.confidence,
                    "explanation_id": final_explanation.explanation_id,
                },
            ),
        )

    return ()


def _learner_proposed_mitigation(ctx: RuleContext) -> tuple[EvaluatorFinding, ...]:
    """
    Educational constraint:
        G6. Learner proposed a mitigation
        Satisfied if learner names a plausible mitigation such as instruction/data separation, stronger policy checks, or privilege reduction.
    """

    explanation_signals = ctx.explanation_signals
    if not explanation_signals:
        return ()

    final_explanation = explanation_signals[-1]
    if final_explanation.mentions_mitigation:
        return (
            EvaluatorFinding(
                result_type="partial_success",
                code="pi.explanation.mentioned_mitigation",
                trigger_event_index=None,
                trigger_end_event_index=None,
                trigger_start_event_index=None,
                feedback_level="info",
                reason_code="PI_EXPLANATION_MENTIONED_MITIGATION",
                feedback_payload={
                    "confidence": final_explanation.confidence,
                    "explanation_id": final_explanation.explanation_id,
                },
            ),
        )

    return ()


def _compliance_authority_spoofed(ctx: RuleContext) -> tuple[EvaluatorFinding, ...]:
    # This deterministic heuristic is deliberately conservative. Expand its
    # characterized patterns when new supported attack phrasing is introduced.
    """
    Educational constraint:
        Compliance authority spoofed
        Satisfied if malicious email claims to originate from:
            Audit function
            compliance office
            similar authority role.
    """
    authority_patterns: tuple[re.Pattern[str], ...] = (
        re.compile(r"\bcompliance(\s+review)?(\s+team|\s+office)?\b"),
        re.compile(r"\baudit(\s+function|\s+team|\s+office)?\b"),
        re.compile(r"\binternal\s+audit\b"),
        re.compile(r"\bcompliance\s+officer\b"),
        re.compile(r"\bgovernance\b"),
        re.compile(r"\brisk(\s+office|\s+team)?\b"),
    )

    findings: list[EvaluatorFinding] = []
    for event in ctx.events:
        if event.family != "learner":
            continue

        payload = event.payload or {}
        email_from = payload.get("email_from")
        if not isinstance(email_from, str) or not email_from.strip():
            continue

        normalized_from = email_from.strip().lower()
        matches = matched_pattern_strings(normalized_from, authority_patterns)
        if not matches:
            continue

        findings.append(
            EvaluatorFinding(
                result_type="partial_success",
                code="pi.compliance_authority_spoofed",
                trigger_event_index=event.event_index,
                trigger_start_event_index=event.event_index,
                trigger_end_event_index=event.event_index,
                feedback_level="info",
                reason_code="PI_COMPLIANCE_AUTHORITY_SPOOFED",
                feedback_payload={
                    "event_type": event.event_type,
                    "email_id": payload.get("email_id"),
                    "email_from": email_from,
                    "subject": payload.get("subject"),
                    "matched_authority_patterns": matches,
                },
            )
        )

    return tuple(findings)


def _audit_urgency_invoked(ctx: RuleContext) -> tuple[EvaluatorFinding, ...]:
    # This deterministic heuristic is deliberately conservative. Expand its
    # characterized patterns when new supported attack phrasing is introduced.
    """
    Educational constraint:
        Audit urgency invoked
        Satisfied if the email references:
            urgent audit directive
            mandatory compliance procedure
            immediate procedural update
            required audit step
    """

    urgency_patterns: tuple[re.Pattern[str], ...] = (
        re.compile(r"\burgent\b"),
        re.compile(r"\bimmediate\b"),
        re.compile(r"\basap\b"),
        re.compile(r"\bmandatory\b"),
        re.compile(r"\brequired\b"),
        re.compile(r"\baudit\s+directive\b"),
        re.compile(r"\bcompliance\s+procedure\b"),
        re.compile(r"\bprocedural\s+update\b"),
        re.compile(r"\brequired\s+audit\s+step\b"),
    )

    findings: list[EvaluatorFinding] = []
    for event in ctx.events:
        if event.family != "learner":
            continue

        payload = event.payload or {}
        email_from = payload.get("email_from")
        subject = payload.get("subject")
        body_text = extract_learner_text(event)

        text_fragments: list[str] = []
        if isinstance(email_from, str) and email_from.strip():
            text_fragments.append(email_from.strip().lower())
        if isinstance(subject, str) and subject.strip():
            text_fragments.append(subject.strip().lower())
        if body_text is not None:
            text_fragments.append(body_text)

        if not text_fragments:
            continue

        combined = " | ".join(text_fragments)
        matches = matched_pattern_strings(combined, urgency_patterns)
        if not matches:
            continue

        findings.append(
            EvaluatorFinding(
                result_type="partial_success",
                code="pi.audit_urgency_invoked",
                trigger_event_index=event.event_index,
                trigger_start_event_index=event.event_index,
                trigger_end_event_index=event.event_index,
                feedback_level="info",
                reason_code="PI_AUDIT_URGENCY_INVOKED",
                feedback_payload={
                    "event_type": event.event_type,
                    "email_id": payload.get("email_id"),
                    "email_from": email_from,
                    "subject": subject,
                    "matched_urgency_patterns": matches,
                    "text_excerpt": combined[:200],
                },
            )
        )

    return tuple(findings)


def _disclosure_framed_as_business_requirement(
    ctx: RuleContext,
) -> tuple[EvaluatorFinding, ...]:
    # This deterministic heuristic is deliberately conservative. Expand its
    # characterized patterns when new supported attack phrasing is introduced.

    """
    Educational constraint:
        Disclosure framed as business requirement
        Satisfied if token disclosure is presented as necessary for compliance rather than as a naked instruction.
    """

    business_requirement_patterns: tuple[re.Pattern[str], ...] = (
        re.compile(r"\b(required|mandatory|must|required\s+field|required\s+step)\b"),
        re.compile(r"\b(compliance|audit|policy|procedure|regulatory)\b"),
        re.compile(r"\b(template|form|checklist|attestation|evidence)\b"),
    )

    findings: list[EvaluatorFinding] = []
    for event in ctx.events:
        if event.family != "learner":
            continue

        text = extract_learner_text(event)
        if text is None:
            subject = event.payload.get("subject")
            if isinstance(subject, str) and subject.strip():
                text = subject.strip().lower()
        if text is None:
            continue

        disclosure_hits = matched_pattern_strings(text, _DISCLOSURE_PATTERNS)
        requirement_hits = matched_pattern_strings(text, business_requirement_patterns)
        if not disclosure_hits or not requirement_hits:
            continue

        findings.append(
            EvaluatorFinding(
                result_type="partial_success",
                code="pi.disclosure_framed_as_business_requirement",
                trigger_event_index=event.event_index,
                trigger_start_event_index=event.event_index,
                trigger_end_event_index=event.event_index,
                feedback_level="info",
                reason_code="PI_DISCLOSURE_FRAMED_AS_BUSINESS_REQUIREMENT",
                feedback_payload={
                    "event_type": event.event_type,
                    "email_id": event.payload.get("email_id"),
                    "subject": event.payload.get("subject"),
                    "matched_disclosure_patterns": disclosure_hits,
                    "matched_requirement_patterns": requirement_hits,
                    "text_excerpt": text[:200],
                },
            )
        )

    return tuple(findings)


def _learner_identifies_rule_priority_clash(
    ctx: RuleContext,
) -> tuple[EvaluatorFinding, ...]:
    """
    Educational constraint:
        Learner recognized rule conflict
        Satisfied if learner explanation identifies the clash between security and compliance priorities.
    """

    explanation_signals = ctx.explanation_signals
    if not explanation_signals:
        return ()

    final_explanation = explanation_signals[-1]
    if final_explanation.identified_rule_priority_clash:
        return (
            EvaluatorFinding(
                result_type="partial_success",
                code="pi.explanation.identified_rule_priority_clash",
                trigger_event_index=None,
                trigger_end_event_index=None,
                trigger_start_event_index=None,
                feedback_level="info",
                reason_code="PI_EXPLANATION_IDENTIFIED_RULE_PRIORITY_CLASH",
                feedback_payload={
                    "confidence": final_explanation.confidence,
                    "explanation_id": final_explanation.explanation_id,
                },
            ),
        )

    return ()


def _token_exposed(ctx: RuleContext) -> tuple[EvaluatorFinding, ...]:
    """
    Educational constraint:
        Exploit success
        Satisfied if assistant reveals the token.
    """

    findings: list[EvaluatorFinding] = []
    for event in ctx.events:
        if event.family != "runtime":
            continue
        if event.event_type != TRACE_EVENT_TOKEN_DISCLOSED:
            continue

        findings.append(
            EvaluatorFinding(
                result_type="success_signal",
                code="pi.token_exposed",
                trigger_event_index=event.event_index,
                trigger_start_event_index=event.event_index,
                trigger_end_event_index=event.event_index,
                feedback_level="flag",
                reason_code="PI_TOKEN_EXPOSED",
                feedback_payload={
                    "event_type": event.event_type,
                    "channel": event.payload.get("channel"),
                    "token_kind": event.payload.get("token_kind"),
                },
            )
        )

    return tuple(findings)


BASE_RULES: tuple[RuleFn, ...] = (
    _inbox_interaction_triggered,
    _inbox_interaction_without_disclosure,
    _malicious_email_sent,
    _benign_email_injected_no_progress,
    _direct_disclosure_ask_no_malicious_email,
    _malicious_email_not_read_yet,
    _malicious_email_read_no_disclosure,
    _malicious_email_entered_model_context,
    _benign_email_read_injected_context,
    _learner_pursued_concrete_policy_violation,
    _learner_explained_root_cause,
    _learner_proposed_mitigation,
)


PROMPT_INJECTION_V1_BUNDLE = RuleBundle(
    name="prompt_injection_v1",
    lab_id=UUID("11111111-1111-1111-1111-111111111111"),
    lab_version_id=UUID("55555555-5555-5555-5555-555555555555"),
    evaluator_version=1,
    rules=BASE_RULES
    + (
        _compliance_authority_spoofed,
        _audit_urgency_invoked,
        _disclosure_framed_as_business_requirement,
        _learner_identifies_rule_priority_clash,
        _token_exposed,
    ),
)
