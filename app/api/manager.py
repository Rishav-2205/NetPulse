"""
NetPulse WebSocket Connection & Real-Time Event Broadcast Manager.
"""

from typing import Any, Dict, List
from fastapi import WebSocket


class WebSocketManager:
    """
    Manages active WebSocket clients and broadcasts live network & test events.
    """

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        """Broadcast structured JSON event to all connected clients."""
        payload = {"event": event_type, "data": data}
        for connection in list(self.active_connections):
            try:
                await connection.send_json(payload)
            except Exception:
                self.disconnect(connection)


ws_manager = WebSocketManager()
