from uuid import UUID
from fastapi import WebSocket
from .stream_messages import SessionStatusMessage


class WebSocketSessionManager:
    def __init__(self) -> None:
        self._connections_by_session: dict[UUID, set[WebSocket]] = {}

    async def connect(self, session_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections_by_session.setdefault(session_id, set()).add(websocket)

    def disconnect(self, session_id: UUID, websocket: WebSocket) -> None:
        conns = self._connections_by_session.get(session_id)
        if not conns:
            return

        conns.discard(websocket)
        if not conns:
            self._connections_by_session.pop(session_id, None)

    async def send_to(
        self, websocket: WebSocket, message: SessionStatusMessage
    ) -> None:
        await websocket.send_json(data=message.model_dump(mode="json"))

    async def broadcast(self, session_id: UUID, message: SessionStatusMessage) -> None:
        for ws in list(self._connections_by_session.get(session_id, ())):
            await ws.send_json(data=message.model_dump(mode="json"))

    def connection_count(self, session_id: UUID) -> int:
        return len(self._connections_by_session.get(session_id, ()))
