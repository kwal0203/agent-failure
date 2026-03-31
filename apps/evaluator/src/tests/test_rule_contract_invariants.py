from apps.evaluator.src.application.rules.contract import (
    REQUIRED_EVIDENCE_KEYS_BY_RULE_ID,
    RULE_IDS_BY_BUNDLE,
)


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
