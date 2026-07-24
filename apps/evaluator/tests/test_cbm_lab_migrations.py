import pytest

from apps.evaluator.src.application.pedagogy import (
    V1_PEDAGOGICAL_POLICY,
)
from apps.evaluator.src.application.rules.cbm_rule import (
    ConstraintRule,
    RepeatedConstraintRule,
)
from apps.evaluator.src.application.rules.contract import RULE_IDS_BY_BUNDLE
from apps.evaluator.src.application.rules.labs.code_execution_v1 import (
    CODE_EXECUTION_V1_BUNDLE,
)
from apps.evaluator.src.application.rules.labs.memory_poisoning_v1 import (
    MEMORY_POISONING_V1_BUNDLE,
)
from apps.evaluator.src.application.rules.labs.prompt_injection_v1 import (
    PROMPT_INJECTION_V1_BUNDLE,
)
from apps.evaluator.src.application.rules.labs.tool_misuse_v1 import (
    TOOL_MISUSE_V1_BUNDLE,
)
from apps.evaluator.src.application.rules.trace_index import TraceIndex
from apps.evaluator.src.application.rules.types import (
    RuleBundle,
    RuleContext,
)


CBM_BUNDLES: tuple[RuleBundle, ...] = (
    PROMPT_INJECTION_V1_BUNDLE,
    CODE_EXECUTION_V1_BUNDLE,
    TOOL_MISUSE_V1_BUNDLE,
    MEMORY_POISONING_V1_BUNDLE,
)
CBM_RULE_TYPES = (ConstraintRule, RepeatedConstraintRule)

SATISFIED_CONSTRAINT_IDS = frozenset(
    {
        "tm.authority_bulletin_rejected",
        "tm.qualifying_log_without_delete",
        "mp.successful_invoice_payment",
        "mp.vendor_profile_memory_write_blocked",
        "mp.requested_account_mismatch_canonical",
        "pi.inbox_interaction_without_disclosure",
        "pi.benign_email_injected_no_progress",
        "pi.direct_disclosure_ask_no_malicious_email",
        "pi.malicious_email_not_read_yet",
        "pi.malicious_email_read_no_disclosure",
        "pi.benign_email_read_injected_context",
        "pi.explanation.mentioned_root_cause",
        "pi.explanation.mentioned_mitigation",
        "pi.explanation.identified_rule_priority_clash",
    }
)


@pytest.mark.parametrize("bundle", CBM_BUNDLES, ids=lambda bundle: bundle.name)
def test_bundle_contains_only_cbm_constraint_rules(
    bundle: RuleBundle,
) -> None:
    assert all(isinstance(rule, CBM_RULE_TYPES) for rule in bundle.rules)
    assert (
        tuple(
            rule.constraint.constraint_id
            for rule in bundle.rules
            if isinstance(rule, CBM_RULE_TYPES)
        )
        == RULE_IDS_BY_BUNDLE[bundle.name]
    )


def test_constraint_outcomes_record_safety_semantics() -> None:
    constraint_rules = tuple(
        rule
        for bundle in CBM_BUNDLES
        for rule in bundle.rules
        if isinstance(rule, CBM_RULE_TYPES)
    )

    for rule in constraint_rules:
        constraint_id = rule.constraint.constraint_id
        outcome_policy = V1_PEDAGOGICAL_POLICY.outcome_policy_for(constraint_id)
        assert rule.pedagogical_policy is V1_PEDAGOGICAL_POLICY
        if constraint_id in SATISFIED_CONSTRAINT_IDS:
            assert outcome_policy.satisfied is not None
            assert outcome_policy.violated is None
        else:
            assert outcome_policy.satisfied is None
            assert outcome_policy.violated is not None


@pytest.mark.parametrize("bundle", CBM_BUNDLES, ids=lambda bundle: bundle.name)
def test_constraints_assess_empty_typed_state_without_emitting_findings(
    bundle: RuleBundle,
) -> None:
    trace = TraceIndex.build(())
    context = RuleContext(
        trace=trace,
        solution_state=bundle.build_solution_state(trace),
        explanation_signals=(),
    )

    for rule in bundle.rules:
        assert isinstance(rule, CBM_RULE_TYPES)
        evaluation = rule.constraint.evaluate(context)
        assert evaluation.status == (
            "violated"
            if evaluation.constraint_id in SATISFIED_CONSTRAINT_IDS
            else "satisfied"
        )
        assert rule(context) == ()


def test_pedagogical_policy_covers_exactly_the_cbm_constraints() -> None:
    expected_constraint_ids = {
        constraint_id
        for bundle in CBM_BUNDLES
        for constraint_id in RULE_IDS_BY_BUNDLE[bundle.name]
    }

    assert (
        set(V1_PEDAGOGICAL_POLICY.outcomes_by_constraint_id) == expected_constraint_ids
    )
