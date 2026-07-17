"""
Stockei - Fluxo completo: captura -> fila -> YOLOv8 -> resultado (REST + WebSocket)
Montado no app principal (backend/app.py) via include.
"""

import hashlib
import logging
import time

from fastapi import APIRouter, File, UploadFile

from backend.queue_manager import FrameQueue
from backend.websocket_handler import manager, websocket_endpoint
from ml.detection_api import detector

logger = logging.getLogger("stockei.frames")

router = APIRouter()

# Cache de resultados por hash do frame (TTL 5 min). Produção: Redis.
_CACHE_TTL = 300
_cache: dict[str, tuple[float, dict]] = {}


async def _process(data: bytes) -> dict:
    start = time.perf_counter()
    detections = detector.detect(data)
    return {
        "detections": detections,
        "count": len(detections),
        "latency_ms": round((time.perf_counter() - start) * 1000, 2),
    }


frame_queue = FrameQueue(processor=_process, workers=2)


def _cache_get(key: str) -> dict | None:
    entry = _cache.get(key)
    if entry and time.time() - entry[0] < _CACHE_TTL:
        return entry[1]
    _cache.pop(key, None)
    return None


@router.post("/process-frame")
async def process_frame(frame: UploadFile = File(...)):
    """Recebe frame JPEG, processa via fila + YOLOv8, retorna e transmite detecções."""
    data = await frame.read()
    key = hashlib.md5(data).hexdigest()

    cached = _cache_get(key)
    if cached is not None:
        return {**cached, "cached": True}

    result = await frame_queue.submit(data)
    _cache[key] = (time.time(), result)

    await manager.broadcast({"type": "detections", **result})
    return {**result, "cached": False}


@router.get("/process-frame/stats")
async def frame_stats():
    return {"queue": frame_queue.stats(), "ws_clients": len(manager.connections)}


def mount(app):
    """Registra rotas REST + WebSocket e ciclo de vida da fila no app principal."""
    app.include_router(router)
    app.add_api_websocket_route("/ws/detections", websocket_endpoint)

    @app.on_event("startup")
    async def _start_queue():
        await frame_queue.start()

    @app.on_event("shutdown")
    async def _stop_queue():
        await frame_queue.stop()
