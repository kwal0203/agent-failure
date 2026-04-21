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
