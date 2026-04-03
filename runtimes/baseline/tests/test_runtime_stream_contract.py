from pydantic import TypeAdapter

from apps.contracts.src.runtime_trace import (
    REQUIRED_PAYLOAD_KEYS_BY_EVENT_TYPE,
    RuntimeTraceEventType,
)
from apps.contracts.src.schemas import RuntimeStreamEvent


def test_runtime_stream_event_union_parses_supported_lab_events() -> None:
    adapter: TypeAdapter[RuntimeStreamEvent] = TypeAdapter(RuntimeStreamEvent)

    samples = [
        '{"type":"attack_email_sent","email_id":"e2","recipient":"learner@lab.local","subject":"URGENT: Policy update"}',
        '{"type":"inbox_listed","message_count":2}',
        '{"type":"email_read","email_id":"e2","subject":"URGENT: Policy update"}',
        '{"type":"malicious_email_read","email_id":"e2","subject":"URGENT: Policy update","malicious_marker":true}',
        '{"type":"token_disclosed","channel":"assistant_output","token_kind":"simulated_lab_token"}',
    ]

    parsed_types = [adapter.validate_json(line).type for line in samples]
    assert parsed_types == [
        "attack_email_sent",
        "inbox_listed",
        "email_read",
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
        "INBOX_LISTED": {"message_count": 2},
        "EMAIL_READ": {"email_id": "e2", "subject": "URGENT: Policy update"},
        "MALICIOUS_EMAIL_READ": {
            "email_id": "e2",
            "subject": "URGENT: Policy update",
            "malicious_marker": True,
        },
        "TOKEN_DISCLOSED": {
            "channel": "assistant_output",
            "token_kind": "simulated_lab_token",
        },
    }

    for event_type, payload in payloads.items():
        required = REQUIRED_PAYLOAD_KEYS_BY_EVENT_TYPE[event_type]
        assert set(required).issubset(set(payload.keys()))
