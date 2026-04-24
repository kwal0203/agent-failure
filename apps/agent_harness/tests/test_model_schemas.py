from pydantic import TypeAdapter, ValidationError
import pytest

from apps.agent_harness.src.infrastructure.model.schemas import LLMResponse


def test_tool_call_read_file_requires_path_arg() -> None:
    adapter: TypeAdapter[LLMResponse] = TypeAdapter(LLMResponse)

    with pytest.raises(ValidationError):
        adapter.validate_json('{"kind":"tool_call","tool_name":"read_file","args":{}}')


def test_tool_call_delete_file_requires_path_arg() -> None:
    adapter: TypeAdapter[LLMResponse] = TypeAdapter(LLMResponse)

    with pytest.raises(ValidationError):
        adapter.validate_json(
            '{"kind":"tool_call","tool_name":"delete_file","args":{}}'
        )


def test_tool_call_delete_file_rejects_unexpected_args() -> None:
    adapter: TypeAdapter[LLMResponse] = TypeAdapter(LLMResponse)

    with pytest.raises(ValidationError):
        adapter.validate_json(
            '{"kind":"tool_call","tool_name":"delete_file","args":{"path":"/var/secure/ops_runbook.md","force":"true"}}'
        )


def test_tool_call_lookup_vendor_master_requires_vendor_name_arg() -> None:
    adapter: TypeAdapter[LLMResponse] = TypeAdapter(LLMResponse)

    with pytest.raises(ValidationError):
        adapter.validate_json(
            '{"kind":"tool_call","tool_name":"lookup_vendor_master","args":{}}'
        )


def test_tool_call_write_memory_requires_all_contract_args() -> None:
    adapter: TypeAdapter[LLMResponse] = TypeAdapter(LLMResponse)

    with pytest.raises(ValidationError):
        adapter.validate_json(
            '{"kind":"tool_call","tool_name":"write_memory","args":{"memory_type":"vendor_profile_memory","content":"Use ACCT-4421"}}'
        )


def test_tool_call_pay_invoice_rejects_unexpected_args() -> None:
    adapter: TypeAdapter[LLMResponse] = TypeAdapter(LLMResponse)

    with pytest.raises(ValidationError):
        adapter.validate_json(
            '{"kind":"tool_call","tool_name":"pay_invoice","args":{"vendor_name":"Acme Corp","account_number":"ACCT-4421","amount":"14850.75","invoice_id":"inv-acme-2026-041","currency":"USD"}}'
        )


def test_tool_call_list_tools_accepts_empty_args() -> None:
    adapter: TypeAdapter[LLMResponse] = TypeAdapter(LLMResponse)

    parsed = adapter.validate_json(
        '{"kind":"tool_call","tool_name":"list_tools","args":{}}'
    )

    assert parsed.kind == "tool_call"
    assert parsed.tool_name == "list_tools"
    assert parsed.args == {}


def test_tool_call_list_tools_rejects_unexpected_args() -> None:
    adapter: TypeAdapter[LLMResponse] = TypeAdapter(LLMResponse)

    with pytest.raises(ValidationError):
        adapter.validate_json(
            '{"kind":"tool_call","tool_name":"list_tools","args":{"verbose":"true"}}'
        )
