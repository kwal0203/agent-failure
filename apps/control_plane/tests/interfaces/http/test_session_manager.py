import asyncio
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest
from fastapi import WebSocket

from apps.control_plane.src.interfaces.http.session_manager import (
    WebSocketSessionManager,
)
from apps.control_plane.src.interfaces.http.stream_messages import (
    ServerMessageEnvelope,
    SystemErrorPayload,
)


class _FakeWebSocket:
    def __init__(
        self,
        *,
        delivery_started: asyncio.Event | None = None,
        release_delivery: asyncio.Event | None = None,
        error: Exception | None = None,
    ) -> None:
        self.accepted = False
        self.messages: list[dict[str, object]] = []
        self._delivery_started = delivery_started
        self._release_delivery = release_delivery
        self._error = error

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, data: dict[str, object]) -> None:
        if self._delivery_started is not None:
            self._delivery_started.set()
        if self._release_delivery is not None:
            await self._release_delivery.wait()
        if self._error is not None:
            raise self._error
        self.messages.append(data)


@pytest.mark.asyncio
async def test_broadcast_is_concurrent_failure_isolated_and_prunes_failed_sockets() -> (
    None
):
    manager = WebSocketSessionManager()
    session_id = uuid4()
    slow_started = asyncio.Event()
    release_slow = asyncio.Event()
    slow = _FakeWebSocket(
        delivery_started=slow_started,
        release_delivery=release_slow,
    )
    healthy = _FakeWebSocket()
    failed = _FakeWebSocket(error=RuntimeError("connection closed"))
    for websocket in (slow, healthy, failed):
        await manager.connect(session_id, cast(WebSocket, websocket))

    message = ServerMessageEnvelope(
        type="SYSTEM_ERROR",
        session_id=session_id,
        timestamp=datetime.now(UTC),
        payload=SystemErrorPayload(error_code="TEST", message="hello"),
    )
    broadcast = asyncio.create_task(manager.broadcast(session_id, message))

    await slow_started.wait()
    await asyncio.sleep(0)
    assert len(healthy.messages) == 1
    release_slow.set()
    await broadcast

    assert len(slow.messages) == 1
    assert manager.connection_count(session_id) == 2

    await manager.broadcast(session_id, message)
    assert len(healthy.messages) == 2
    assert len(slow.messages) == 2
