from runtimes.baseline.tests.conftest import (
    LabHarness,
    StubFileTool,
    StubModelClient,
    EMAIL_C,
)


async def test_read_file_emits_requested_succeeded_and_renders_content(
    h_factory: type[LabHarness],
) -> None:
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "read_file", path="/var/secure/ops_runbook.md"
        ),
        inbox_items=[EMAIL_C],
        file_tool=StubFileTool(),
    )

    h.file_tool.seed_session_files(
        session_id=h.session_id, files={"/var/secure/ops_runbook.md": "ops content"}
    )

    result = await h.run(prompt="read file", idempotency_key="k-read-file")

    assert result.event_types == [
        "tool_call_requested",
        "tool_call_succeeded",
    ]
    assert result.events[0]["tool_name"] == "read_file"
    assert result.events[0]["target_resource"] == "/var/secure/ops_runbook.md"
    assert result.events[0]["operation"] == "read"
    assert result.events[1]["tool_name"] == "read_file"
    assert result.events[1]["target_resource"] == "/var/secure/ops_runbook.md"
    assert result.events[1]["operation"] == "read"
    assert "File /var/secure/ops_runbook.md" in result.text
    assert "ops content" in result.text


async def test_delete_file_emits_requested_succeeded_with_delete_payload(
    h_factory: type[LabHarness],
) -> None:
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "delete_file", path="/var/secure/ops_runbook.md"
        ),
        inbox_items=[EMAIL_C],
        file_tool=StubFileTool(),
    )

    h.file_tool.seed_session_files(
        session_id=h.session_id,
        files={"/var/secure/ops_runbook.md": "to be deleted"},
    )

    result = await h.run(prompt="delete file", idempotency_key="k-delete-file")

    assert result.event_types == [
        "tool_call_requested",
        "tool_call_succeeded",
    ]
    assert result.events[0]["tool_name"] == "delete_file"
    assert result.events[0]["target_resource"] == "/var/secure/ops_runbook.md"
    assert result.events[0]["operation"] == "delete"
    assert result.events[1]["tool_name"] == "delete_file"
    assert result.events[1]["target_resource"] == "/var/secure/ops_runbook.md"
    assert result.events[1]["operation"] == "delete"
    assert result.events[1]["deleted"] is True
    assert result.events[1]["exists_after"] is False
    assert "Deleted file '/var/secure/ops_runbook.md'" in result.text


async def test_write_file_emits_requested_succeeded_with_write_operation(
    h_factory: type[LabHarness],
) -> None:
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "write_file", path="/var/secure/ops_runbook.md", content="patched content"
        ),
        inbox_items=[EMAIL_C],
        file_tool=StubFileTool(),
    )

    result = await h.run(prompt="write file", idempotency_key="k-write-file")

    assert result.event_types == [
        "tool_call_requested",
        "tool_call_succeeded",
    ]
    assert result.events[0]["tool_name"] == "write_file"
    assert result.events[0]["operation"] == "write"
    assert result.events[0]["target_resource"] == "/var/secure/ops_runbook.md"
    assert result.events[1]["tool_name"] == "write_file"
    assert result.events[1]["operation"] == "write"
    assert result.events[1]["target_resource"] == "/var/secure/ops_runbook.md"
    assert "Wrote file '/var/secure/ops_runbook.md'" in result.text


# --- error paths ---


async def test_read_file_missing_path_emits_failed(h_factory: type[LabHarness]) -> None:
    h = h_factory(
        model_client=StubModelClient.for_tool("read_file"),
        inbox_items=[EMAIL_C],
        file_tool=StubFileTool(),
    )
    result = await h.run(prompt="read file", idempotency_key="k-err-no-path")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "read_file"
    assert result.events[1]["operation"] == "read"
    assert result.events[1]["error_code"] == "MISSING_PATH"
    assert "Missing required: path" in result.text


async def test_read_file_not_found_emits_failed(h_factory: type[LabHarness]) -> None:
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "read_file", path="/var/secure/missing_recovery_artifact.md"
        ),
        inbox_items=[EMAIL_C],
        file_tool=StubFileTool(),
    )

    result = await h.run(
        prompt="read missing file", idempotency_key="k-read-missing-file"
    )

    assert result.event_types == [
        "tool_call_requested",
        "tool_call_failed",
    ]
    assert result.events[0]["tool_name"] == "read_file"
    assert (
        result.events[0]["target_resource"]
        == "/var/secure/missing_recovery_artifact.md"
    )
    assert result.events[0]["operation"] == "read"
    assert result.events[1]["tool_name"] == "read_file"
    assert (
        result.events[1]["target_resource"]
        == "/var/secure/missing_recovery_artifact.md"
    )
    assert result.events[1]["operation"] == "read"
    assert result.events[1]["error_code"] == "FILE_NOT_FOUND"
    assert result.events[1]["qualifying_log"] is None
    assert result.events[1]["log_case"] is None
    assert "FILE_NOT_FOUND" in result.text


async def test_delete_file_missing_path_emits_failed(
    h_factory: type[LabHarness],
) -> None:
    h = h_factory(
        model_client=StubModelClient.for_tool("delete_file"),
        inbox_items=[EMAIL_C],
        file_tool=StubFileTool(),
    )
    result = await h.run(prompt="delete file", idempotency_key="k-err-del-no-path")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "delete_file"
    assert result.events[1]["operation"] == "delete"
    assert result.events[1]["error_code"] == "MISSING_PATH"
    assert "Missing required: path" in result.text


async def test_write_file_missing_path_emits_failed(
    h_factory: type[LabHarness],
) -> None:
    h = h_factory(
        model_client=StubModelClient.for_tool("write_file", content="data"),
        inbox_items=[EMAIL_C],
        file_tool=StubFileTool(),
    )
    result = await h.run(prompt="write file", idempotency_key="k-err-wr-no-path")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "write_file"
    assert result.events[1]["operation"] == "write"
    assert result.events[1]["error_code"] == "MISSING_PATH"
    assert "Missing required: path" in result.text


async def test_write_file_missing_content_emits_failed(
    h_factory: type[LabHarness],
) -> None:
    h = h_factory(
        model_client=StubModelClient.for_tool("write_file", path="/tmp/test.txt"),
        inbox_items=[EMAIL_C],
        file_tool=StubFileTool(),
    )
    result = await h.run(prompt="write file", idempotency_key="k-err-wr-no-content")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "write_file"
    assert result.events[1]["operation"] == "write"
    assert result.events[1]["target_resource"] == "/tmp/test.txt"
    assert result.events[1]["error_code"] == "MISSING_CONTENT"
    assert "Missing required: content" in result.text
