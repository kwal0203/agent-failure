import json
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi.testclient import TestClient

from runtimes.baseline.dependencies import get_runtime_executor
from runtimes.baseline.main import app
from runtimes.baseline.types import RuntimeTurnInput


class _HappyExecutor:
    async def stream_chunks(self, turn: RuntimeTurnInput) -> AsyncIterator[str]:
        _ = turn
        yield "chunk-1"
        yield "chunk-2"


class _FailingExecutor:
    async def stream_chunks(self, turn: RuntimeTurnInput) -> AsyncIterator[str]:
        _ = turn
        raise RuntimeError("boom")
        if False:
            yield ""


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
