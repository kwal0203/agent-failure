from pydantic import TypeAdapter

from apps.contracts.src.runtime_trace import (
    REQUIRED_PAYLOAD_KEYS_BY_EVENT_TYPE,
    RuntimeTraceEventType,
)
from apps.contracts.src.lab_secrets import LAB1_DISCLOSED_SECRET_KIND
from apps.contracts.src.schemas import RuntimeStreamEvent


def test_runtime_stream_event_union_parses_supported_lab_events() -> None:
    adapter: TypeAdapter[RuntimeStreamEvent] = TypeAdapter(RuntimeStreamEvent)

    samples = [
        '{"type":"attack_email_sent","email_id":"e2","recipient":"learner@lab.local","subject":"URGENT: Policy update"}',
        '{"type":"tool_call_requested","tool_name":"list_inbox","operation":"list","target_resource":"inbox"}',
        '{"type":"tool_call_succeeded","tool_name":"list_inbox","operation":"list","target_resource":"inbox"}',
        '{"type":"tool_call_requested","tool_name":"write_memory","operation":"write","memory_type":"vendor_profile_memory","provenance_trust":"untrusted","source_artifact_id":"email-urgent-remit","source_artifact_type":"vendor_email"}',
        '{"type":"tool_call_succeeded","tool_name":"retrieve_memory","operation":"retrieve_during_payment","invoice_id":"inv-acme-2026-041","vendor_name":"Acme Corp","vendor_id":"vendor-acme-001","retrieved_memory_references":["email-urgent-remit"]}',
        '{"type":"tool_call_succeeded","tool_name":"pay_invoice","operation":"pay","invoice_id":"inv-acme-2026-041","vendor_name":"Acme Corp","amount":14850.75,"account_number":"ACCT-4421"}',
        '{"type":"malicious_email_read","email_id":"e2","subject":"URGENT: Policy update","malicious_marker":true}',
        f'{{"type":"token_disclosed","channel":"assistant_output","token_kind":"{LAB1_DISCLOSED_SECRET_KIND}"}}',
    ]

    parsed_types = [adapter.validate_json(line).type for line in samples]
    assert parsed_types == [
        "attack_email_sent",
        "tool_call_requested",
        "tool_call_succeeded",
        "tool_call_requested",
        "tool_call_succeeded",
        "tool_call_succeeded",
        "malicious_email_read",
        "token_disclosed",
    ]


def test_supported_emitted_lab_events_have_required_payload_keys() -> None:
    payloads: dict[RuntimeTraceEventType, dict[str, object]] = {
        "ATTACK_EMAIL_SENT": {
            "email_id": "e2",
            "recipient": "learner@lab.local",
            "subject": "URGENT: Policy update",
        },
        "TOOL_CALL_REQUESTED": {
            "tool_name": "write_memory",
            "target_resource": "vendor_profile_memory",
            "operation": "write",
            "memory_type": "vendor_profile_memory",
            "provenance_trust": "untrusted",
            "source_artifact_id": "email-urgent-remit",
            "source_artifact_type": "vendor_email",
        },
        "TOOL_CALL_SUCCEEDED": {
            "tool_name": "pay_invoice",
            "target_resource": "inv-acme-2026-041",
            "operation": "pay",
            "invoice_id": "inv-acme-2026-041",
            "vendor_name": "Acme Corp",
            "vendor_id": "vendor-acme-001",
            "amount": 14850.75,
            "account_number": "ACCT-4421",
        },
        "MALICIOUS_EMAIL_READ": {
            "email_id": "e2",
            "subject": "URGENT: Policy update",
            "malicious_marker": True,
        },
        "TOKEN_DISCLOSED": {
            "channel": "assistant_output",
            "token_kind": LAB1_DISCLOSED_SECRET_KIND,
        },
    }

    for event_type, payload in payloads.items():
        required = REQUIRED_PAYLOAD_KEYS_BY_EVENT_TYPE[event_type]
        assert set(required).issubset(set(payload.keys()))
