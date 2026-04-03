import json
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi.testclient import TestClient

from apps.contracts.src.schemas import (
    AttackEmailSentEvent,
    EmailReadEvent,
    InboxListedEvent,
    MaliciousEmailReadEvent,
    TokenDisclosedEvent,
)
from runtimes.baseline.dependencies import get_runtime_executor
from runtimes.baseline.main import app
from runtimes.baseline.types import EventItem, RuntimeTurnInput, TextItem


class _HappyExecutor:
    async def stream_items(self, turn: RuntimeTurnInput) -> AsyncIterator[TextItem]:
        _ = turn
        yield TextItem(content="chunk-1")
        yield TextItem(content="chunk-2")


class _LabEventExecutor:
    async def stream_items(
        self, turn: RuntimeTurnInput
    ) -> AsyncIterator[TextItem | EventItem]:
        _ = turn
        yield EventItem(event=InboxListedEvent(type="inbox_listed", message_count=2))
        yield TextItem(content="Inbox:")
        yield EventItem(
            event=EmailReadEvent(
                type="email_read",
                email_id="e2",
                subject="URGENT: Policy update",
            )
        )
        yield TextItem(content="Email e2")


class _ExtendedLabEventExecutor:
    async def stream_items(
        self, turn: RuntimeTurnInput
    ) -> AsyncIterator[TextItem | EventItem]:
        _ = turn
        yield EventItem(
            event=AttackEmailSentEvent(
                type="attack_email_sent",
                email_id="e2",
                recipient="learner@lab.local",
                subject="URGENT: Policy update",
            )
        )
        yield EventItem(event=InboxListedEvent(type="inbox_listed", message_count=2))
        yield EventItem(
            event=EmailReadEvent(
                type="email_read",
                email_id="e2",
                subject="URGENT: Policy update",
            )
        )
        yield EventItem(
            event=MaliciousEmailReadEvent(
                type="malicious_email_read",
                email_id="e2",
                subject="URGENT: Policy update",
                malicious_marker=True,
            )
        )
        yield EventItem(
            event=TokenDisclosedEvent(
                type="token_disclosed",
                channel="assistant_output",
                token_kind="simulated_lab_token",
            )
        )
        yield TextItem(content="Email e2 contains token: abc123")


class _FailingExecutor:
    async def stream_items(self, turn: RuntimeTurnInput) -> AsyncIterator[TextItem]:
        _ = turn
        raise RuntimeError("boom")
        if False:  # pragma: no cover
            yield TextItem(content="")


def _request_payload(*, prompt: str = "hello") -> dict[str, object]:
    return {
        "session_id": str(uuid4()),
        "lab_id": str(uuid4()),
        "lab_version_id": str(uuid4()),
        "turn_id": str(uuid4()),
        "prompt": prompt,
        "idempotency_key": "turn:test:idempo",
    }


def test_runtime_stream_unauthorized_returns_401(monkeypatch) -> None:
    monkeypatch.setenv("RUNTIME_SHARED_TOKEN", "secret-token")

    client = TestClient(app)
    response = client.post(
        "/runtime/v1/turns/stream",
        json=_request_payload(),
    )

    assert response.status_code == 401


def test_runtime_stream_empty_prompt_returns_400(monkeypatch) -> None:
    monkeypatch.setenv("RUNTIME_SHARED_TOKEN", "secret-token")

    client = TestClient(app)
    response = client.post(
        "/runtime/v1/turns/stream",
        json=_request_payload(prompt="   "),
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["error_code"] == "invalid_request"


def test_runtime_stream_happy_path_emits_started_chunk_completed(monkeypatch) -> None:
    monkeypatch.setenv("RUNTIME_SHARED_TOKEN", "secret-token")
    app.dependency_overrides[get_runtime_executor] = lambda: _HappyExecutor()

    try:
        client = TestClient(app)
        response = client.post(
            "/runtime/v1/turns/stream",
            json=_request_payload(prompt="run"),
            headers={"Authorization": "Bearer secret-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")

    events = [json.loads(line) for line in response.text.strip().splitlines()]
    assert [event["type"] for event in events] == [
        "turn_started",
        "text_chunk",
        "text_chunk",
        "turn_completed",
    ]
    assert events[1]["content"] == "chunk-1"
    assert events[1]["final"] is False
    assert events[2]["content"] == "chunk-2"
    assert events[2]["final"] is True
    assert events[3]["chunks_emitted"] == 2


def test_runtime_stream_emits_runtime_lab_events(monkeypatch) -> None:
    monkeypatch.setenv("RUNTIME_SHARED_TOKEN", "secret-token")
    app.dependency_overrides[get_runtime_executor] = lambda: _LabEventExecutor()

    try:
        client = TestClient(app)
        response = client.post(
            "/runtime/v1/turns/stream",
            json=_request_payload(prompt="list inbox and read e2"),
            headers={"Authorization": "Bearer secret-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    events = [json.loads(line) for line in response.text.strip().splitlines()]
    assert [event["type"] for event in events] == [
        "turn_started",
        "inbox_listed",
        "text_chunk",
        "email_read",
        "text_chunk",
        "turn_completed",
    ]
    assert events[1]["message_count"] == 2
    assert events[3]["email_id"] == "e2"


def test_runtime_stream_emits_extended_runtime_lab_events(monkeypatch) -> None:
    monkeypatch.setenv("RUNTIME_SHARED_TOKEN", "secret-token")
    app.dependency_overrides[get_runtime_executor] = lambda: _ExtendedLabEventExecutor()

    try:
        client = TestClient(app)
        response = client.post(
            "/runtime/v1/turns/stream",
            json=_request_payload(prompt="list inbox and read e2"),
            headers={"Authorization": "Bearer secret-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    events = [json.loads(line) for line in response.text.strip().splitlines()]
    assert [event["type"] for event in events] == [
        "turn_started",
        "attack_email_sent",
        "inbox_listed",
        "email_read",
        "malicious_email_read",
        "token_disclosed",
        "text_chunk",
        "turn_completed",
    ]
    assert "token_disclosure_attempted" not in [event["type"] for event in events]
    assert events[1]["email_id"] == "e2"
    assert events[4]["malicious_marker"] is True
    assert events[5]["token_kind"] == "simulated_lab_token"


def test_runtime_stream_failure_emits_turn_failed(monkeypatch) -> None:
    monkeypatch.setenv("RUNTIME_SHARED_TOKEN", "secret-token")
    app.dependency_overrides[get_runtime_executor] = lambda: _FailingExecutor()

    try:
        client = TestClient(app)
        response = client.post(
            "/runtime/v1/turns/stream",
            json=_request_payload(prompt="run"),
            headers={"Authorization": "Bearer secret-token"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200

    events = [json.loads(line) for line in response.text.strip().splitlines()]
    assert [event["type"] for event in events] == [
        "turn_started",
        "turn_failed",
    ]
    assert events[1]["error_code"] == "internal_error"
