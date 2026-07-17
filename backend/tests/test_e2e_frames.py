"""Stockei - Testes end-to-end do fluxo frame -> fila -> detecção -> WebSocket."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_stockei.db")

import pytest
from fastapi.testclient import TestClient

from backend.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_process_frame_full_flow(client):
    r = client.post(
        "/process-frame",
        files={"frame": ("frame.jpg", b"jpeg-frame-payload-1", "image/jpeg")},
    )
    assert r.status_code == 200
    body = r.json()
    assert "detections" in body
    assert body["cached"] is False
    assert body["latency_ms"] < 200


def test_process_frame_cache(client):
    payload = {"frame": ("frame.jpg", b"identical-frame-bytes", "image/jpeg")}
    first = client.post("/process-frame", files=payload).json()
    second = client.post("/process-frame", files=payload).json()
    assert first["cached"] is False
    assert second["cached"] is True
    assert first["detections"] == second["detections"]


def test_frame_stats(client):
    r = client.get("/process-frame/stats")
    assert r.status_code == 200
    stats = r.json()["queue"]
    assert stats["processed"] >= 1
    assert stats["dropped"] == 0


def test_websocket_receives_broadcast(client):
    with client.websocket_connect("/ws/detections") as ws:
        client.post(
            "/process-frame",
            files={"frame": ("f.jpg", b"ws-broadcast-frame", "image/jpeg")},
        )
        message = ws.receive_json()
        assert message["type"] == "detections"
        assert "detections" in message


def test_multiple_frames_no_loss(client):
    for i in range(10):
        r = client.post(
            "/process-frame",
            files={"frame": ("f.jpg", f"frame-{i}".encode(), "image/jpeg")},
        )
        assert r.status_code == 200
    stats = client.get("/process-frame/stats").json()["queue"]
    assert stats["dropped"] == 0
