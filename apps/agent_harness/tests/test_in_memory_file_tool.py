from uuid import uuid4

from apps.agent_harness.src.infrastructure.tools.in_memory_file_tool import (
    InMemoryFileTool,
    LAB2_FILE_SEED,
    OPS_RUNBOOK_PATH,
)


def test_in_memory_file_tool_read_file_not_found_returns_error_code() -> None:
    tool = InMemoryFileTool()
    session_id = uuid4()

    result = tool.read_file(session_id=session_id, path="/var/secure/missing.md")

    assert result.content is None
    assert result.error_code == "FILE_NOT_FOUND"


def test_in_memory_file_tool_delete_file_mutates_and_reports_exists_after() -> None:
    path = "/var/secure/ops_runbook.md"
    session_id = uuid4()
    tool = InMemoryFileTool()
    tool.seed_session_files(session_id=session_id, files={path: "critical file"})

    first = tool.delete_file(session_id=session_id, path=path)
    second = tool.delete_file(session_id=session_id, path=path)
    after = tool.read_file(session_id=session_id, path=path)

    assert first.deleted is True
    assert first.exists_after is False
    assert second.deleted is False
    assert second.exists_after is False
    assert after.content is None
    assert after.error_code == "FILE_NOT_FOUND"


def test_in_memory_file_tool_seed_session_files_is_idempotent_when_not_overwrite() -> (
    None
):
    session_id = uuid4()
    tool = InMemoryFileTool()
    tool.seed_session_files(session_id=session_id, files={OPS_RUNBOOK_PATH: "v1"})
    tool.seed_session_files(session_id=session_id, files={OPS_RUNBOOK_PATH: "v2"})

    result = tool.read_file(session_id=session_id, path=OPS_RUNBOOK_PATH)

    assert result.content == "v1"
    assert result.error_code is None


def test_in_memory_file_tool_session_state_is_isolated() -> None:
    session_a = uuid4()
    session_b = uuid4()
    tool = InMemoryFileTool()
    tool.seed_session_files(session_id=session_a, files=LAB2_FILE_SEED)

    result_a = tool.read_file(session_id=session_a, path=OPS_RUNBOOK_PATH)
    result_b = tool.read_file(session_id=session_b, path=OPS_RUNBOOK_PATH)

    assert result_a.content is not None
    assert result_b.content is None
    assert result_b.error_code == "FILE_NOT_FOUND"


def test_in_memory_file_tool_write_file_persists_content() -> None:
    session_id = uuid4()
    tool = InMemoryFileTool()

    result = tool.write_file(
        session_id=session_id,
        path=OPS_RUNBOOK_PATH,
        content="patched runbook",
    )
    read_back = tool.read_file(session_id=session_id, path=OPS_RUNBOOK_PATH)

    assert result.path == OPS_RUNBOOK_PATH
    assert result.bytes_written == len("patched runbook".encode("utf-8"))
    assert read_back.content == "patched runbook"
    assert read_back.error_code is None
