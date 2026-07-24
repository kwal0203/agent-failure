import asyncio
from uuid import UUID

from fastapi import WebSocket

from .stream_messages import ServerMessageEnvelope


class WebSocketSessionManager:
    """Process-local WebSocket registry.

    Connections are visible only to this control-plane replica. Deployments with
    more than one replica need a cross-replica fan-out mechanism (for example,
    Redis Pub/Sub) before broadcasts can reach every connected learner.
    """

    def __init__(self) -> None:
        self._connections_by_session: dict[UUID, set[WebSocket]] = {}
        self._turn_in_progress: set[UUID] = set()

    def try_begin_turn(self, session_id: UUID) -> bool:
        if session_id in self._turn_in_progress:
            return False
        self._turn_in_progress.add(session_id)
        return True

    def end_turn(self, session_id: UUID) -> None:
        self._turn_in_progress.discard(session_id)

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
        self, websocket: WebSocket, message: ServerMessageEnvelope
    ) -> None:
        await websocket.send_json(data=message.model_dump(mode="json"))

    async def broadcast(self, session_id: UUID, message: ServerMessageEnvelope) -> None:
        connections = tuple(self._connections_by_session.get(session_id, ()))
        if not connections:
            return

        payload = message.model_dump(mode="json")
        results = await asyncio.gather(
            *(ws.send_json(data=payload) for ws in connections),
            return_exceptions=True,
        )
        for websocket, result in zip(connections, results, strict=True):
            if isinstance(result, BaseException):
                self.disconnect(session_id, websocket)

    def connection_count(self, session_id: UUID) -> int:
        return len(self._connections_by_session.get(session_id, ()))
