from apps.evaluator.src.application.rules.contract import (
    REASON_CODE_BY_RULE_ID,
    REQUIRED_EVIDENCE_KEYS_BY_RULE_ID,
    RULE_DEFINITIONS,
    RULE_DEFINITION_BY_ID,
    RULE_IDS_BY_BUNDLE,
)
from apps.evaluator.src.application.pedagogy import V1_PEDAGOGICAL_POLICY


def _all_rule_ids_from_bundles() -> list[str]:
    rule_ids: list[str] = []
    for bundle_rule_ids in RULE_IDS_BY_BUNDLE.values():
        rule_ids.extend(bundle_rule_ids)
    return rule_ids


def test_every_bundle_rule_id_exists_in_evidence_map() -> None:
    all_rule_ids = _all_rule_ids_from_bundles()
    for rule_id in all_rule_ids:
        assert rule_id in REQUIRED_EVIDENCE_KEYS_BY_RULE_ID


def test_evidence_map_has_no_unknown_rule_ids() -> None:
    all_rule_ids = set(_all_rule_ids_from_bundles())
    for rule_id in REQUIRED_EVIDENCE_KEYS_BY_RULE_ID:
        assert rule_id in all_rule_ids


def test_no_duplicate_rule_ids_across_bundles() -> None:
    all_rule_ids = _all_rule_ids_from_bundles()
    assert len(all_rule_ids) == len(set(all_rule_ids))


def test_all_contract_lookups_are_derived_from_typed_definitions() -> None:
    assert tuple(RULE_DEFINITION_BY_ID.values()) == RULE_DEFINITIONS
    assert set(REASON_CODE_BY_RULE_ID) == set(RULE_DEFINITION_BY_ID)
    for definition in RULE_DEFINITIONS:
        assert (
            REQUIRED_EVIDENCE_KEYS_BY_RULE_ID[definition.rule_id]
            == definition.evidence_keys
        )
        assert REASON_CODE_BY_RULE_ID[definition.rule_id] == definition.reason_code


def test_pedagogical_policy_reason_codes_match_rule_definitions() -> None:
    for definition in RULE_DEFINITIONS:
        outcome_policy = V1_PEDAGOGICAL_POLICY.outcomes_by_constraint_id[
            definition.rule_id
        ]
        presentation = outcome_policy.satisfied or outcome_policy.violated
        assert presentation is not None
        assert presentation.reason_code == definition.reason_code


def test_rule_definition_rejects_incomplete_metadata() -> None:
    from apps.evaluator.src.application.rules.contract import RuleDefinition

    try:
        RuleDefinition(
            rule_id="",
            bundle="test_v1",
            evidence_keys=("event_type",),
            reason_code="TEST",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("blank rule IDs must fail closed")

    try:
        RuleDefinition(
            rule_id="test.rule",
            bundle="test_v1",
            evidence_keys=(),
            reason_code="TEST",
        )
    except ValueError:
        pass
    else:
        raise AssertionError("missing evidence metadata must fail closed")
