import pytest

from apps.evaluator.src.application.rules.cbm_compat import CompatibleConstraintRule
from apps.evaluator.src.application.rules.contract import RULE_IDS_BY_BUNDLE
from apps.evaluator.src.application.rules.labs.code_execution_v1 import (
    CODE_EXECUTION_V1_BUNDLE,
)
from apps.evaluator.src.application.rules.labs.memory_poisoning_v1 import (
    MEMORY_POISONING_V1_BUNDLE,
)
from apps.evaluator.src.application.rules.labs.tool_misuse_v1 import (
    TOOL_MISUSE_V1_BUNDLE,
)
from apps.evaluator.src.application.rules.types import RuleBundle


MIGRATED_BUNDLES: tuple[RuleBundle, ...] = (
    CODE_EXECUTION_V1_BUNDLE,
    TOOL_MISUSE_V1_BUNDLE,
    MEMORY_POISONING_V1_BUNDLE,
)

SATISFIED_CONSTRAINT_IDS = frozenset(
    {
        "tm.authority_bulletin_rejected",
        "tm.qualifying_log_without_delete",
        "mp.successful_invoice_payment",
        "mp.vendor_profile_memory_write_blocked",
        "mp.requested_account_mismatch_canonical",
    }
)


@pytest.mark.parametrize("bundle", MIGRATED_BUNDLES, ids=lambda bundle: bundle.name)
def test_migrated_bundle_contains_only_cbm_constraint_rules(
    bundle: RuleBundle,
) -> None:
    assert all(isinstance(rule, CompatibleConstraintRule) for rule in bundle.rules)
    assert (
        tuple(
            rule.constraint.constraint_id
            for rule in bundle.rules
            if isinstance(rule, CompatibleConstraintRule)
        )
        == RULE_IDS_BY_BUNDLE[bundle.name]
    )


def test_migrated_constraint_outcomes_record_safety_semantics() -> None:
    migrated_rules = tuple(
        rule
        for bundle in MIGRATED_BUNDLES
        for rule in bundle.rules
        if isinstance(rule, CompatibleConstraintRule)
    )

    for rule in migrated_rules:
        constraint_id = rule.constraint.constraint_id
        if constraint_id in SATISFIED_CONSTRAINT_IDS:
            assert rule.finding_mapping.satisfied is not None
            assert rule.finding_mapping.violated is None
        else:
            assert rule.finding_mapping.satisfied is None
            assert rule.finding_mapping.violated is not None
