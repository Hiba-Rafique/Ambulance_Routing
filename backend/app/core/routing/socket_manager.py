from typing import List, Dict, Set
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        # Map request_id to a list of active websockets
        # This allows multiple clients (e.g. patient + admin) to track the same request
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # Track which request_ids have active simulations to prevent duplicates
        self.active_simulations: Set[int] = set()

    async def connect(self, websocket: WebSocket, request_id: int):
        await websocket.accept()
        if request_id not in self.active_connections:
            self.active_connections[request_id] = []
        self.active_connections[request_id].append(websocket)

    def disconnect(self, websocket: WebSocket, request_id: int):
        if request_id in self.active_connections:
            if websocket in self.active_connections[request_id]:
                self.active_connections[request_id].remove(websocket)
            if not self.active_connections[request_id]:
                del self.active_connections[request_id]

    async def broadcast(self, message: dict, request_id: int):
        if request_id in self.active_connections:
            for connection in self.active_connections[request_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    # Handle broken pipe or closed connection gracefully
                    pass

    def start_simulation(self, request_id: int) -> bool:
        """Mark a simulation as started. Returns True if this is the first start, False if already running."""
        if request_id in self.active_simulations:
            return False
        self.active_simulations.add(request_id)
        return True

    def end_simulation(self, request_id: int):
        """Mark a simulation as ended."""
        self.active_simulations.discard(request_id)

manager = ConnectionManager()
