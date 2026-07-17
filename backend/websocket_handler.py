"""
Stockei - WebSocket para resultados de detecção em tempo real.
"""

import logging

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger("stockei.ws")


class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)
        logger.info("WS conectado (%d ativos)", len(self.connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)
        logger.info("WS desconectado (%d ativos)", len(self.connections))

    async def broadcast(self, message: dict):
        """Envia resultado a todos os clientes; remove conexões mortas."""
        dead = []
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # mantém conexão viva; cliente pode enviar pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
