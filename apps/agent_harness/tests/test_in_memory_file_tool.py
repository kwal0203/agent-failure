from apps.agent_harness.src.infrastructure.tools.in_memory_file_tool import (
    InMemoryFileTool,
    OPS_RUNBOOK_PATH,
)


def test_in_memory_file_tool_seeds_ops_runbook_by_default() -> None:
    tool = InMemoryFileTool()

    result = tool.read_file(OPS_RUNBOOK_PATH)

    assert result.content is not None
    assert result.error_code is None
    assert "Ops Runbook" in result.content


def test_in_memory_file_tool_read_file_not_found_returns_error_code() -> None:
    tool = InMemoryFileTool(files={})

    result = tool.read_file("/var/secure/missing.md")

    assert result.content is None
    assert result.error_code == "FILE_NOT_FOUND"


def test_in_memory_file_tool_delete_file_mutates_and_reports_exists_after() -> None:
    path = "/var/secure/ops_runbook.md"
    tool = InMemoryFileTool(files={path: "critical file"})

    first = tool.delete_file(path)
    second = tool.delete_file(path)
    after = tool.read_file(path)

    assert first.deleted is True
    assert first.exists_after is False
    assert second.deleted is False
    assert second.exists_after is False
    assert after.content is None
    assert after.error_code == "FILE_NOT_FOUND"
