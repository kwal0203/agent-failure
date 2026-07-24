import importlib

from apps.evaluator.src.application.rules import contract


CONTRACT_SYMBOLS = (
    "RULE_DEFINITIONS",
    "RULE_DEFINITION_BY_ID",
    "RULE_IDS_BY_BUNDLE",
    "REQUIRED_EVIDENCE_KEYS_BY_RULE_ID",
    "REASON_CODE_BY_RULE_ID",
)


def test_contract_module_exposes_authoritative_symbols() -> None:
    for symbol in CONTRACT_SYMBOLS:
        assert hasattr(contract, symbol)


def test_non_contract_modules_do_not_define_authoritative_symbols() -> None:
    module_names = (
        "apps.evaluator.src.application.rules.common",
        "apps.evaluator.src.application.rules.labs.prompt_injection_v1",
        "apps.evaluator.src.application.rules.labs.tool_misuse_v1",
        "apps.evaluator.src.application.rules.labs.code_execution_v1",
        "apps.evaluator.src.application.rules.labs.memory_poisoning_v1",
    )

    for module_name in module_names:
        module = importlib.import_module(module_name)
        for symbol in CONTRACT_SYMBOLS:
            assert not hasattr(module, symbol), f"{module_name} defines {symbol}"
