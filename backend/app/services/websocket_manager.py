from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect


class ConnectionManager:
    """Manage WebSocket connections for organisation memberships."""

    def __init__(self) -> None:
        self.active_connections: dict[UUID, set[WebSocket]] = {}

    def connect(
        self,
        membership_id: UUID,
        websocket: WebSocket,
    ) -> None:
        """Register an already accepted WebSocket connection."""

        connections = self.active_connections.setdefault(
            membership_id,
            set(),
        )

        connections.add(websocket)

    def disconnect(
        self,
        membership_id: UUID,
        websocket: WebSocket,
    ) -> None:
        """Remove a disconnected WebSocket."""

        connections = self.active_connections.get(membership_id)

        if connections is None:
            return

        connections.discard(websocket)

        if not connections:
            self.active_connections.pop(membership_id, None)

    async def send_to_member(
        self,
        membership_id: UUID,
        message: dict,
    ) -> None:
        """Send a JSON message to all connections of one member."""

        connections = self.active_connections.get(membership_id)

        if not connections:
            return

        disconnected = []

        for websocket in list(connections):
            try:
                await websocket.send_json(message)
            except (WebSocketDisconnect, RuntimeError, OSError):
                disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect(membership_id, websocket)


manager = ConnectionManager()
