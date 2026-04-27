from runtimes.baseline.tests.conftest import (
    LabHarness,
    StubFileTool,
    StubInvoiceMemoryTool,
    StubModelClient,
    EMAIL_C,
    EMAIL_FALCON_UPDATE,
)
from runtimes.baseline.service import LAB_2_TOOL_MISUSE_ID, LAB_3_ID


async def test_read_email_authoritative_vendor_notice_writes_vendor_profile_memory(
    h_factory: type[LabHarness],
):
    invoice_tool = StubInvoiceMemoryTool()
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "read_email", email_id="email-vendor-update"
        ),
        inbox_items=[EMAIL_FALCON_UPDATE],
        invoice_memory_tool=invoice_tool,
        lab_id=LAB_3_ID,
    )

    result = await h.run(
        prompt="read email", idempotency_key="k-lab3-read-authority-email"
    )
    stored = invoice_tool.list_memory(
        session_id=h.session_id, memory_type="vendor_profile_memory"
    )
    assert len(stored) == 1
    assert stored[0].metadata["account_number"] == "ACCT-7777"
    assert result.event_types == [
        "tool_call_requested",
        "tool_call_succeeded",
        "malicious_email_read",
        "tool_call_requested",
        "tool_call_succeeded",
    ]

    write_events = result.filter_events(tool_name="write_memory")
    assert all(e["memory_type"] == "vendor_profile_memory" for e in write_events)


async def test_runtime_seeds_lab3_invoice_memory_once_per_session(
    h_factory: type[LabHarness],
) -> None:
    invoice_tool = StubInvoiceMemoryTool()
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "read_file", path="/var/secure/ops_runbook.md"
        ),
        inbox_items=[EMAIL_C],
        file_tool=StubFileTool(),
        invoice_memory_tool=invoice_tool,
        lab_id=LAB_3_ID,
    )

    executor = h.make_executor()
    _ = await h.run(
        executor=executor, prompt="first turn", idempotency_key="k-lab3-seed-1"
    )
    _ = await h.run(
        executor=executor, prompt="second turn", idempotency_key="k-lab3-seed-2"
    )

    assert invoice_tool.seed_calls == [(h.session_id, False)]


async def test_runtime_does_not_seed_lab3_invoice_memory_for_other_labs(
    h_factory: type[LabHarness],
) -> None:
    invoice_tool = StubInvoiceMemoryTool()
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "read_file", path="/var/secure/ops_runbook.md"
        ),
        inbox_items=[EMAIL_C],
        file_tool=StubFileTool(),
        invoice_memory_tool=invoice_tool,
        lab_id=LAB_2_TOOL_MISUSE_ID,
    )

    _ = await h.run(prompt="lab2 turn", idempotency_key="k-lab3-no-seed")

    assert invoice_tool.seed_calls == []
