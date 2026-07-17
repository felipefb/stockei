"""Stockei - Testes da API de detecção."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from ml.detection_api import MockDetector, app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert "detector" in r.json()


def test_detect_endpoint():
    r = client.post("/detect", files={"image": ("frame.jpg", b"fake-jpeg-data-123", "image/jpeg")})
    assert r.status_code == 200
    body = r.json()
    assert "detections" in body and "latency_ms" in body
    assert body["count"] == len(body["detections"])
    for det in body["detections"]:
        assert set(det) == {"class_id", "class_name", "confidence", "bbox"}
        assert len(det["bbox"]) == 4
        assert 0 <= det["confidence"] <= 1


def test_detect_latency_under_100ms():
    r = client.post("/detect", files={"image": ("f.jpg", b"x" * 10_000, "image/jpeg")})
    assert r.json()["latency_ms"] < 100


def test_mock_detector_deterministic():
    d = MockDetector()
    img = b"same-image-bytes"
    assert d.detect(img) == d.detect(img)
