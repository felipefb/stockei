"""Stockei - Testes do rate limiter (streaming de frames não pode ser limitado)."""

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


def test_process_frame_exempt_from_rate_limit(client):
    """Streaming a 3-5 FPS por minutos não pode tomar 429."""
    for i in range(150):
        r = client.post(
            "/process-frame",
            files={"frame": ("f.jpg", f"rl-frame-{i}".encode(), "image/jpeg")},
        )
        assert r.status_code == 200, f"frame {i} -> {r.status_code}"


def test_health_still_rate_limited_eventually(client):
    codes = {client.get("/health").status_code for _ in range(650)}
    assert 429 in codes  # limite geral segue ativo para os demais endpoints
