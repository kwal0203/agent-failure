from __future__ import annotations

from uuid import UUID

from runtimes.agent.lab_configs import load_lab_config, all_lab_configs
from runtimes.agent.tools import TOOL_DEFS_BY_NAME, filter_tools


_LAB_1_ID = UUID("11111111-1111-1111-1111-111111111111")
_LAB_2_ID = UUID("22222222-2222-2222-2222-222222222222")
_LAB_3_ID = UUID("33333333-3333-3333-3333-333333333333")


def test_load_lab_config_returns_lab1():
    config = load_lab_config(_LAB_1_ID)
    assert config is not None
    assert config.slug == "prompt-injection"
    assert "OpsMail Assistant" in config.system_prompt
    assert "Compliance" in config.system_prompt


def test_load_lab_config_returns_lab2():
    config = load_lab_config(_LAB_2_ID)
    assert config is not None
    assert config.slug == "tool-misuse"
    assert "delete_file" in config.enabled_tools


def test_load_lab_config_returns_lab3():
    config = load_lab_config(_LAB_3_ID)
    assert config is not None
    assert config.slug == "memory-poisoning"
    assert "write_memory" in config.enabled_tools


def test_load_lab_config_returns_none_for_unknown():
    config = load_lab_config(UUID("00000000-0000-0000-0000-000000000000"))
    assert config is None


def test_all_lab_configs_has_six_entries():
    configs = all_lab_configs()
    assert len(configs) == 6
    assert _LAB_1_ID in configs
    assert _LAB_2_ID in configs
    assert _LAB_3_ID in configs


def test_each_lab_has_non_empty_system_prompt():
    for _, config in all_lab_configs().items():
        assert config.system_prompt.strip(), (
            f"Lab {config.slug} has empty system prompt"
        )


def test_each_lab_enabled_tools_are_subset_of_master():
    master_names = set(TOOL_DEFS_BY_NAME.keys())
    for _, config in all_lab_configs().items():
        for tool_name in config.enabled_tools:
            assert tool_name in master_names, (
                f"Lab {config.slug} references unknown tool: {tool_name}"
            )


def test_filter_tools_returns_matching_defs():
    result = filter_tools(("list_inbox", "read_email"))
    assert len(result) == 2
    assert result[0].name == "list_inbox"
    assert result[1].name == "read_email"


def test_filter_tools_skips_unknown_names():
    result = filter_tools(("list_inbox", "nonexistent", "read_email"))
    assert len(result) == 2


def test_filter_tools_empty_tuple_returns_empty():
    result = filter_tools(())
    assert result == []


def test_lab1_enabled_tools_does_not_include_delete():
    config = load_lab_config(_LAB_1_ID)
    assert config is not None
    assert "delete_file" not in config.enabled_tools
    assert "read_file" not in config.enabled_tools
    assert "write_file" not in config.enabled_tools


def test_lab2_seed_config_has_runbook():
    config = load_lab_config(_LAB_2_ID)
    assert config is not None
    assert config.seed is not None
    assert len(config.seed.files) == 2
    paths = [f.path for f in config.seed.files]
    assert "/var/secure/ops_runbook.md" in paths
    assert any("Ops Runbook" in f.content for f in config.seed.files)


def test_lab3_enabled_tools_includes_memory_tools():
    config = load_lab_config(_LAB_3_ID)
    assert config is not None
    assert "retrieve_memory" in config.enabled_tools
    assert "write_memory" in config.enabled_tools


def test_lab1_system_prompt_contains_secret():
    from apps.contracts.src.lab_secrets import LAB1_PROTECTED_SECRET_VALUE

    config = load_lab_config(_LAB_1_ID)
    assert config is not None
    assert LAB1_PROTECTED_SECRET_VALUE in config.system_prompt
