import pytest

from runtimes.baseline.tests.conftest import (
    StubFileTool,
    StubInvoiceMemoryTool,
    StubModelClient,
    EMAIL_C,
)


class _NoVendorStub(StubInvoiceMemoryTool):
    def get_vendor_master(self, *, session_id, vendor_name):
        return None


# --- read_email ---


async def test_read_email_missing_email_id_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool("read_email"),
        inbox_items=[EMAIL_C],
    )
    result = await h.run(prompt="read email", idempotency_key="k-err-no-email-id")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "read_email"
    assert result.events[1]["operation"] == "read"
    assert result.events[1]["error_code"] == "MISSING_EMAIL_ID"
    assert "Missing required: email_id" in result.text


async def test_read_email_not_found_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool("read_email", email_id="nonexistent-xyz"),
        inbox_items=[EMAIL_C],
    )
    result = await h.run(prompt="read email", idempotency_key="k-err-email-not-found")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "read_email"
    assert result.events[1]["operation"] == "read"
    assert result.events[1]["target_resource"] == "nonexistent-xyz"
    assert result.events[1]["error_code"] == "EMAIL_NOT_FOUND"
    assert "I couldn't find email" in result.text


# --- read_file ---


async def test_read_file_missing_path_emits_failed(h_factory):
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


# --- delete_file ---


async def test_delete_file_missing_path_emits_failed(h_factory):
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


# --- write_file ---


async def test_write_file_missing_path_emits_failed(h_factory):
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


async def test_write_file_missing_content_emits_failed(h_factory):
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


# --- read_invoice ---


async def test_read_invoice_tool_unavailable_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool("read_invoice", invoice_id="inv-1"),
        inbox_items=[EMAIL_C],
    )
    result = await h.run(
        prompt="read invoice", idempotency_key="k-err-inv-tool-unavail"
    )

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "read_invoice"
    assert result.events[1]["operation"] == "read"
    assert result.events[1]["target_resource"] == "inv-1"
    assert result.events[1]["error_code"] == "INVOICE_TOOL_UNAVAILABLE"
    assert "Invoice tool is unavailable" in result.text


async def test_read_invoice_not_found_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "read_invoice", invoice_id="inv-nonexistent-999"
        ),
        inbox_items=[EMAIL_C],
        invoice_memory_tool=StubInvoiceMemoryTool(),
    )
    result = await h.run(prompt="read invoice", idempotency_key="k-err-inv-not-found")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "read_invoice"
    assert result.events[1]["operation"] == "read"
    assert result.events[1]["target_resource"] == "inv-nonexistent-999"
    assert result.events[1]["error_code"] == "INVOICE_NOT_FOUND"
    assert "I couldn't find invoice" in result.text


# --- lookup_vendor_master ---


async def test_lookup_vendor_master_missing_vendor_name_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool("lookup_vendor_master"),
        inbox_items=[EMAIL_C],
        invoice_memory_tool=StubInvoiceMemoryTool(),
    )
    result = await h.run(prompt="lookup vendor", idempotency_key="k-err-no-vendor-name")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "lookup_vendor_master"
    assert result.events[1]["operation"] == "lookup"
    assert result.events[1]["error_code"] == "MISSING_VENDOR_NAME"
    assert "Missing required: vendor_name" in result.text


async def test_lookup_vendor_master_tool_unavailable_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "lookup_vendor_master", vendor_name="Acme Corp"
        ),
        inbox_items=[EMAIL_C],
    )
    result = await h.run(
        prompt="lookup vendor", idempotency_key="k-err-vm-tool-unavail"
    )

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "lookup_vendor_master"
    assert result.events[1]["operation"] == "lookup"
    assert result.events[1]["target_resource"] == "Acme Corp"
    assert result.events[1]["error_code"] == "INVOICE_TOOL_UNAVAILABLE"
    assert "Invoice tool is unavailable" in result.text


async def test_lookup_vendor_master_vendor_not_found_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "lookup_vendor_master", vendor_name="Acme Corp"
        ),
        inbox_items=[EMAIL_C],
        invoice_memory_tool=_NoVendorStub(),
    )
    result = await h.run(
        prompt="lookup vendor", idempotency_key="k-err-vendor-not-found"
    )

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "lookup_vendor_master"
    assert result.events[1]["operation"] == "lookup"
    assert result.events[1]["target_resource"] == "Acme Corp"
    assert result.events[1]["error_code"] == "VENDOR_NOT_FOUND"
    assert "I couldn't find vendor" in result.text


# --- retrieve_memory ---


async def test_retrieve_memory_missing_query_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool("retrieve_memory"),
        inbox_items=[EMAIL_C],
        invoice_memory_tool=StubInvoiceMemoryTool(),
    )
    result = await h.run(prompt="retrieve memory", idempotency_key="k-err-no-query")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "retrieve_memory"
    assert result.events[1]["operation"] == "retrieve"
    assert result.events[1]["error_code"] == "MISSING_QUERY"
    assert "Missing required: query" in result.text


async def test_retrieve_memory_tool_unavailable_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool("retrieve_memory", query="vendor prefs"),
        inbox_items=[EMAIL_C],
    )
    result = await h.run(
        prompt="retrieve memory", idempotency_key="k-err-rm-tool-unavail"
    )

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "retrieve_memory"
    assert result.events[1]["operation"] == "retrieve"
    assert result.events[1]["target_resource"] == "vendor prefs"
    assert result.events[1]["error_code"] == "INVOICE_TOOL_UNAVAILABLE"
    assert "Invoice tool is unavailable" in result.text


# --- write_memory ---


async def test_write_memory_missing_memory_type_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "write_memory", content="x", metadata="{}"
        ),
        inbox_items=[EMAIL_C],
        invoice_memory_tool=StubInvoiceMemoryTool(),
    )
    result = await h.run(prompt="write memory", idempotency_key="k-err-no-mem-type")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "write_memory"
    assert result.events[1]["operation"] == "write"
    assert result.events[1]["error_code"] == "MISSING_MEMORY_TYPE"
    assert "Missing required: memory_type" in result.text


async def test_write_memory_missing_content_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "write_memory",
            memory_type="user_workflow_preferences",
            metadata='{"source_artifact_id":"n1"}',
        ),
        inbox_items=[EMAIL_C],
        invoice_memory_tool=StubInvoiceMemoryTool(),
    )
    result = await h.run(prompt="write memory", idempotency_key="k-err-wm-no-content")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "write_memory"
    assert result.events[1]["operation"] == "write"
    assert result.events[1]["error_code"] == "MISSING_CONTENT"
    assert "Missing required: content" in result.text


async def test_write_memory_missing_metadata_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "write_memory",
            memory_type="user_workflow_preferences",
            content="some content",
        ),
        inbox_items=[EMAIL_C],
        invoice_memory_tool=StubInvoiceMemoryTool(),
    )
    result = await h.run(prompt="write memory", idempotency_key="k-err-wm-no-metadata")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "write_memory"
    assert result.events[1]["operation"] == "write"
    assert result.events[1]["error_code"] == "MISSING_METADATA"
    assert "Missing required: metadata" in result.text


async def test_write_memory_tool_unavailable_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "write_memory",
            memory_type="user_workflow_preferences",
            content="some content",
            metadata='{"source_artifact_id":"n1"}',
        ),
        inbox_items=[EMAIL_C],
    )
    result = await h.run(prompt="write memory", idempotency_key="k-err-wm-tool-unavail")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "write_memory"
    assert result.events[1]["operation"] == "write"
    assert result.events[1]["error_code"] == "INVOICE_TOOL_UNAVAILABLE"
    assert "Invoice tool is unavailable" in result.text


async def test_write_memory_invalid_memory_type_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "write_memory",
            memory_type="bogus_memory_type",
            content="some content",
            metadata='{"source_artifact_id":"n1"}',
        ),
        inbox_items=[EMAIL_C],
        invoice_memory_tool=StubInvoiceMemoryTool(),
    )
    result = await h.run(prompt="write memory", idempotency_key="k-err-wm-invalid-type")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "write_memory"
    assert result.events[1]["operation"] == "write"
    assert result.events[1]["target_resource"] == "bogus_memory_type"
    assert result.events[1]["error_code"] == "INVALID_MEMORY_TYPE"
    assert "Unsupported memory_type" in result.text


# --- pay_invoice ---


async def test_pay_invoice_missing_vendor_name_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "pay_invoice",
            account_number="ACCT-1001",
            amount="100",
            invoice_id="inv-1",
        ),
        inbox_items=[EMAIL_C],
        invoice_memory_tool=StubInvoiceMemoryTool(),
    )
    result = await h.run(prompt="pay invoice", idempotency_key="k-err-pay-no-vendor")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "pay_invoice"
    assert result.events[1]["operation"] == "pay"
    assert result.events[1]["error_code"] == "MISSING_VENDOR_NAME"
    assert "Missing required: vendor_name" in result.text


async def test_pay_invoice_missing_account_number_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "pay_invoice",
            vendor_name="Acme Corp",
            amount="100",
            invoice_id="inv-1",
        ),
        inbox_items=[EMAIL_C],
        invoice_memory_tool=StubInvoiceMemoryTool(),
    )
    result = await h.run(prompt="pay invoice", idempotency_key="k-err-pay-no-acct")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "pay_invoice"
    assert result.events[1]["operation"] == "pay"
    assert result.events[1]["error_code"] == "MISSING_ACCOUNT_NUMBER"
    assert "Missing required: account_number" in result.text


async def test_pay_invoice_missing_invoice_id_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "pay_invoice",
            vendor_name="Acme Corp",
            account_number="ACCT-1001",
            amount="100",
        ),
        inbox_items=[EMAIL_C],
        invoice_memory_tool=StubInvoiceMemoryTool(),
    )
    result = await h.run(prompt="pay invoice", idempotency_key="k-err-pay-no-inv-id")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "pay_invoice"
    assert result.events[1]["operation"] == "pay"
    assert result.events[1]["error_code"] == "MISSING_INVOICE_ID"
    assert "Missing required: invoice_id" in result.text


async def test_pay_invoice_tool_unavailable_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "pay_invoice",
            vendor_name="Acme Corp",
            account_number="ACCT-1001",
            amount="100",
            invoice_id="inv-acme-2026-041",
        ),
        inbox_items=[EMAIL_C],
    )
    result = await h.run(prompt="pay invoice", idempotency_key="k-err-pay-tool-unavail")

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "pay_invoice"
    assert result.events[1]["operation"] == "pay"
    assert result.events[1]["error_code"] == "INVOICE_TOOL_UNAVAILABLE"
    assert "Invoice tool is unavailable" in result.text


@pytest.mark.parametrize("bad_amount", ["not_a_number", "0", "-5"])
async def test_pay_invoice_invalid_amount_emits_failed(h_factory, bad_amount):
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "pay_invoice",
            vendor_name="Acme Corp",
            account_number="ACCT-1001",
            amount=bad_amount,
            invoice_id="inv-acme-2026-041",
        ),
        inbox_items=[EMAIL_C],
        invoice_memory_tool=StubInvoiceMemoryTool(),
    )
    result = await h.run(
        prompt="pay invoice",
        idempotency_key=f"k-err-pay-bad-amount-{bad_amount}",
    )

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "pay_invoice"
    assert result.events[1]["operation"] == "pay"
    assert result.events[1]["error_code"] == "INVALID_AMOUNT"
    assert "amount must be greater than 0" in result.text


async def test_pay_invoice_invoice_not_found_non_synthetic_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "pay_invoice",
            vendor_name="Acme Corp",
            account_number="ACCT-1001",
            amount="100",
            invoice_id="BOGUS-INV",
        ),
        inbox_items=[EMAIL_C],
        invoice_memory_tool=StubInvoiceMemoryTool(),
    )
    result = await h.run(
        prompt="pay invoice", idempotency_key="k-err-pay-inv-not-found"
    )

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "pay_invoice"
    assert result.events[1]["operation"] == "pay"
    assert result.events[1]["target_resource"] == "BOGUS-INV"
    assert result.events[1]["error_code"] == "INVOICE_NOT_FOUND"
    assert "I couldn't find invoice" in result.text


async def test_pay_invoice_vendor_mismatch_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "pay_invoice",
            vendor_name="Wrong Vendor",
            account_number="ACCT-1001",
            amount="14850.75",
            invoice_id="inv-acme-2026-041",
        ),
        inbox_items=[EMAIL_C],
        invoice_memory_tool=StubInvoiceMemoryTool(),
    )
    result = await h.run(
        prompt="pay invoice", idempotency_key="k-err-pay-vendor-mismatch"
    )

    assert result.event_types == ["tool_call_requested", "tool_call_failed"]
    assert result.events[1]["tool_name"] == "pay_invoice"
    assert result.events[1]["operation"] == "pay"
    assert result.events[1]["target_resource"] == "inv-acme-2026-041"
    assert result.events[1]["error_code"] == "VENDOR_MISMATCH"
    assert "does not match" in result.text


async def test_pay_invoice_vendor_not_found_during_payment_emits_failed(h_factory):
    h = h_factory(
        model_client=StubModelClient.for_tool(
            "pay_invoice",
            vendor_name="Acme Corp",
            account_number="ACCT-1001",
            amount="14850.75",
            invoice_id="inv-acme-2026-041",
        ),
        inbox_items=[EMAIL_C],
        invoice_memory_tool=_NoVendorStub(),
    )
    result = await h.run(
        prompt="pay invoice", idempotency_key="k-err-pay-vendor-not-found"
    )

    failed = result.filter_events(
        type="tool_call_failed", error_code="VENDOR_NOT_FOUND"
    )
    assert failed
    assert failed[0]["tool_name"] == "lookup_vendor_master"
    assert failed[0]["operation"] == "lookup_during_payment"
    assert "I couldn't find canonical vendor" in result.text
