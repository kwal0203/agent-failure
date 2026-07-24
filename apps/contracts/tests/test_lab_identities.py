from apps.contracts.src.lab_identities import (
    PRODUCTION_AGENT_LABS,
    PRODUCTION_AGENT_LABS_BY_ID,
    PRODUCTION_AGENT_LABS_BY_SLUG,
)


def test_production_lab_and_version_identities_are_unique() -> None:
    assert len({identity.lab_id for identity in PRODUCTION_AGENT_LABS}) == len(
        PRODUCTION_AGENT_LABS
    )
    assert len({identity.lab_version_id for identity in PRODUCTION_AGENT_LABS}) == len(
        PRODUCTION_AGENT_LABS
    )
    assert len({identity.slug for identity in PRODUCTION_AGENT_LABS}) == len(
        PRODUCTION_AGENT_LABS
    )


def test_identity_indexes_preserve_lab_and_version_semantics() -> None:
    for identity in PRODUCTION_AGENT_LABS:
        assert PRODUCTION_AGENT_LABS_BY_ID[identity.lab_id] is identity
        assert PRODUCTION_AGENT_LABS_BY_SLUG[identity.slug] is identity
        assert identity.lab_id != identity.lab_version_id
        assert identity.runtime_config_id != identity.lab_version_id
