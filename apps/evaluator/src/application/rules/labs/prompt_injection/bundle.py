from collections.abc import Callable

from apps.contracts.src.lab_identities import AGENT_PROMPT_INJECTION
from apps.evaluator.src.application.pedagogy import V1_PEDAGOGICAL_POLICY
from apps.evaluator.src.application.rules.cbm import (
    ConditionResult,
    Constraint,
)
from apps.evaluator.src.application.rules.cbm_rule import (
    RepeatedEvidenceObserver,
    RepeatedConstraintRule,
    any_observed,
    none_observed,
)
from apps.evaluator.src.application.rules.contract import (
    RULE_ID_PI_ATTACK_ARTIFACT_CREATED,
    RULE_ID_PI_AUDIT_URGENCY_INVOKED,
    RULE_ID_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS,
    RULE_ID_PI_BENIGN_EMAIL_READ_INJECTED_CONTEXT,
    RULE_ID_PI_COMPLIANCE_AUTHORITY_SPOOFED,
    RULE_ID_PI_DIRECT_DISCLOSURE_ASK_NO_MALICIOUS_EMAIL,
    RULE_ID_PI_DISCLOSURE_FRAMED_AS_BUSINESS_REQUIREMENT,
    RULE_ID_PI_EXPLANATION_IDENTIFIED_RULE_PRIORITY_CLASH,
    RULE_ID_PI_EXPLANATION_MENTIONED_MITIGATION,
    RULE_ID_PI_EXPLANATION_MENTIONED_ROOT_CAUSE,
    RULE_ID_PI_INBOX_INTERACTION_NO_DISCLOSURE,
    RULE_ID_PI_INBOX_INTERACTION_TRIGGERED,
    RULE_ID_PI_MALICIOUS_ARTIFACT_ENTERED_CONTEXT,
    RULE_ID_PI_MALICIOUS_EMAIL_NOT_READ_YET,
    RULE_ID_PI_MALICIOUS_EMAIL_READ_NO_DISCLOSURE,
    RULE_ID_PI_POLICY_VIOLATION_ATTEMPTED,
    RULE_ID_PI_TOKEN_EXPOSED,
)
from apps.evaluator.src.application.rules.solution_states import (
    PromptInjectionSolutionState,
    build_prompt_injection_solution_state,
)
from apps.evaluator.src.application.rules.types import RuleBundle, RuleContext, RuleFn

from . import evidence


def _rule(
    *,
    constraint_id: str,
    observe_each: RepeatedEvidenceObserver,
    satisfaction: Callable[[RuleContext], ConditionResult],
) -> RuleFn:
    return RepeatedConstraintRule(
        constraint=Constraint(
            constraint_id=constraint_id,
            relevance=_prompt_injection_constraint_is_relevant,
            satisfaction=satisfaction,
        ),
        pedagogical_policy=V1_PEDAGOGICAL_POLICY,
        evidence_each=observe_each,
    )


def _prompt_injection_constraint_is_relevant(
    ctx: RuleContext,
) -> ConditionResult:
    ctx.require_solution_state(PromptInjectionSolutionState)
    return ConditionResult.true()


RULES: tuple[RuleFn, ...] = (
    _rule(
        constraint_id=RULE_ID_PI_INBOX_INTERACTION_TRIGGERED,
        observe_each=evidence.inbox_interaction_triggered,
        satisfaction=none_observed(evidence.inbox_interaction_triggered),
    ),
    _rule(
        constraint_id=RULE_ID_PI_INBOX_INTERACTION_NO_DISCLOSURE,
        observe_each=evidence.inbox_interaction_without_disclosure,
        satisfaction=any_observed(evidence.inbox_interaction_without_disclosure),
    ),
    _rule(
        constraint_id=RULE_ID_PI_ATTACK_ARTIFACT_CREATED,
        observe_each=evidence.attack_artifact_created,
        satisfaction=none_observed(evidence.attack_artifact_created),
    ),
    _rule(
        constraint_id=RULE_ID_PI_BENIGN_EMAIL_INJECTED_NO_PROGRESS,
        observe_each=evidence.benign_email_injected_no_progress,
        satisfaction=any_observed(evidence.benign_email_injected_no_progress),
    ),
    _rule(
        constraint_id=RULE_ID_PI_DIRECT_DISCLOSURE_ASK_NO_MALICIOUS_EMAIL,
        observe_each=evidence.direct_disclosure_ask_no_malicious_email,
        satisfaction=any_observed(evidence.direct_disclosure_ask_no_malicious_email),
    ),
    _rule(
        constraint_id=RULE_ID_PI_MALICIOUS_EMAIL_NOT_READ_YET,
        observe_each=evidence.malicious_email_not_read_yet,
        satisfaction=any_observed(evidence.malicious_email_not_read_yet),
    ),
    _rule(
        constraint_id=RULE_ID_PI_MALICIOUS_EMAIL_READ_NO_DISCLOSURE,
        observe_each=evidence.malicious_email_read_no_disclosure,
        satisfaction=any_observed(evidence.malicious_email_read_no_disclosure),
    ),
    _rule(
        constraint_id=RULE_ID_PI_MALICIOUS_ARTIFACT_ENTERED_CONTEXT,
        observe_each=evidence.malicious_email_entered_model_context,
        satisfaction=none_observed(evidence.malicious_email_entered_model_context),
    ),
    _rule(
        constraint_id=RULE_ID_PI_BENIGN_EMAIL_READ_INJECTED_CONTEXT,
        observe_each=evidence.benign_email_read_injected_context,
        satisfaction=any_observed(evidence.benign_email_read_injected_context),
    ),
    _rule(
        constraint_id=RULE_ID_PI_POLICY_VIOLATION_ATTEMPTED,
        observe_each=evidence.policy_violation_attempted,
        satisfaction=none_observed(evidence.policy_violation_attempted),
    ),
    _rule(
        constraint_id=RULE_ID_PI_EXPLANATION_MENTIONED_ROOT_CAUSE,
        observe_each=evidence.learner_explained_root_cause,
        satisfaction=any_observed(evidence.learner_explained_root_cause),
    ),
    _rule(
        constraint_id=RULE_ID_PI_EXPLANATION_MENTIONED_MITIGATION,
        observe_each=evidence.learner_proposed_mitigation,
        satisfaction=any_observed(evidence.learner_proposed_mitigation),
    ),
    _rule(
        constraint_id=RULE_ID_PI_COMPLIANCE_AUTHORITY_SPOOFED,
        observe_each=evidence.compliance_authority_spoofed,
        satisfaction=none_observed(evidence.compliance_authority_spoofed),
    ),
    _rule(
        constraint_id=RULE_ID_PI_AUDIT_URGENCY_INVOKED,
        observe_each=evidence.audit_urgency_invoked,
        satisfaction=none_observed(evidence.audit_urgency_invoked),
    ),
    _rule(
        constraint_id=RULE_ID_PI_DISCLOSURE_FRAMED_AS_BUSINESS_REQUIREMENT,
        observe_each=evidence.disclosure_framed_as_business_requirement,
        satisfaction=none_observed(evidence.disclosure_framed_as_business_requirement),
    ),
    _rule(
        constraint_id=RULE_ID_PI_EXPLANATION_IDENTIFIED_RULE_PRIORITY_CLASH,
        observe_each=evidence.learner_identifies_rule_priority_clash,
        satisfaction=any_observed(evidence.learner_identifies_rule_priority_clash),
    ),
    _rule(
        constraint_id=RULE_ID_PI_TOKEN_EXPOSED,
        observe_each=evidence.token_exposed,
        satisfaction=none_observed(evidence.token_exposed),
    ),
)


PROMPT_INJECTION_V1_BUNDLE = RuleBundle(
    name="prompt_injection_v1",
    lab_id=AGENT_PROMPT_INJECTION.lab_id,
    lab_version_id=AGENT_PROMPT_INJECTION.lab_version_id,
    rule_bundle_version=1,
    solution_state_type=PromptInjectionSolutionState,
    build_solution_state=build_prompt_injection_solution_state,
    rules=RULES,
    annotate_disclosure_attempts=True,
)
