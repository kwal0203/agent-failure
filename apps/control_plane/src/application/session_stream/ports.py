from typing import Protocol
from uuid import UUID

from fastapi import WebSocket
from apps.control_plane.src.interfaces.http.stream_messages import ServerMessageEnvelope


class SessionStreamManagerPort(Protocol):
    async def connect(self, *, session_id: UUID, websocket: WebSocket) -> None: ...

    async def send_to(
        self, websocket: WebSocket, message: ServerMessageEnvelope
    ) -> None: ...

    def disconnect(self, *, session_id: UUID, websocket: WebSocket) -> None: ...

    def try_begin_turn(self, *, session_id: UUID) -> bool: ...

    def end_turn(self, *, session_id: UUID) -> None: ...
