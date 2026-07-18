"""Stockei - Testes do escaneamento unificado (nome + validade numa passada)."""

import io
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_stockei.db")

import pytest
from fastapi.testclient import TestClient

from backend.app import _rate_state, app
from backend.database import Base, engine


@pytest.fixture(scope="module")
def client():
    _rate_state.clear()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def auth(client):
    client.post("/auth/register", json={
        "email": "scanf@stockei.com", "password": "secret123", "name": "S"})
    token = client.post("/auth/login", json={
        "email": "scanf@stockei.com", "password": "secret123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _label(lines):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (640, 420), "white")
    draw = ImageDraw.Draw(img)
    y = 40
    for text, size in lines:
        try:
            font = ImageFont.truetype("arialbd.ttf", size)
        except OSError:
            font = ImageFont.load_default()
        draw.text((30, y), text, fill="black", font=font)
        y += size + 26
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _post(client, auth, image):
    return client.post("/identify/scan-frame", headers=auth,
                       files={"frame": ("f.jpg", image, "image/jpeg")})


def test_scan_frame_returns_name_and_expiry_together(client, auth):
    future = (date.today() + timedelta(days=200)).strftime("%d/%m/%Y")
    r = _post(client, auth, _label([("VIGOR", 64), ("GREGO Tradicional", 42),
                                    (f"VAL {future}", 30)]))
    assert r.status_code == 200
    body = r.json()
    assert "vigor" in (body["suggested_name"] or "").lower()
    assert body["expiry"] is not None
    assert body["expiry"]["expired"] is False
    assert body["expiry"]["date"] == (date.today() + timedelta(days=200)).isoformat()


def test_scan_frame_accepts_expired_date(client, auth):
    r = _post(client, auth, _label([("LEITE UHT", 54), ("VAL 01/01/2020", 32)]))
    body = r.json()
    assert body["expiry"] is not None
    assert body["expiry"]["expired"] is True
    assert body["expiry"]["date"] == "2020-01-01"


def test_scan_frame_without_date(client, auth):
    r = _post(client, auth, _label([("SABONETE NEUTRO", 54)]))
    body = r.json()
    assert body["expiry"] is None
    assert body["suggested_name"] is not None


def test_scan_frame_requires_auth(client):
    r = client.post("/identify/scan-frame",
                    files={"frame": ("f.jpg", b"x", "image/jpeg")})
    assert r.status_code == 401
