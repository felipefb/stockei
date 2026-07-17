"""Stockei - Testes da identificação visual (OCR local da embalagem)."""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_stockei.db")

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.vision_identify import _prettify, read_package


def _label_image(lines):
    """Gera uma 'embalagem' sintética com textos em tamanhos diferentes."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (640, 480), "white")
    draw = ImageDraw.Draw(img)
    y = 30
    for text, size in lines:
        try:
            font = ImageFont.truetype("arial.ttf", size)
        except OSError:
            font = ImageFont.load_default()
        draw.text((30, y), text, fill="black", font=font)
        y += size + 25
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_read_package_suggests_product_name():
    data = _label_image([
        ("VIGOR", 64),
        ("GREGO Tradicional", 44),
        ("90g", 30),
        ("Industria Brasileira", 14),
    ])
    result = read_package(data)
    assert result["suggested_name"] is not None
    name = result["suggested_name"].lower()
    assert "vigor" in name
    assert "grego" in name


def test_read_package_empty_image():
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (320, 240), "white").save(buf, format="JPEG")
    result = read_package(buf.getvalue())
    assert result["suggested_name"] is None
    assert result["texts"] == []


def test_prettify():
    assert _prettify("VIGORGREGO Tradicional90g") == "Vigorgrego Tradicional 90 G"
    assert _prettify("COCA  COLA") == "Coca Cola"


@pytest.fixture(scope="module")
def client():
    from backend.app import _rate_state
    from backend.database import Base, engine

    _rate_state.clear()  # suites anteriores (test_rate_limit) esgotam a janela
    Base.metadata.create_all(bind=engine)  # test_identify derruba as tabelas
    with TestClient(app) as c:
        yield c


def test_suggest_from_image_endpoint(client):
    client.post("/auth/register", json={
        "email": "vision@stockei.com", "password": "secret123", "name": "V"})
    token = client.post("/auth/login", json={
        "email": "vision@stockei.com", "password": "secret123"}).json()["access_token"]
    data = _label_image([("VIGOR", 64), ("GREGO", 48)])
    r = client.post(
        "/identify/suggest-from-image",
        files={"frame": ("f.jpg", data, "image/jpeg")},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert "vigor" in (r.json()["suggested_name"] or "").lower()


def test_suggest_requires_auth(client):
    r = client.post(
        "/identify/suggest-from-image",
        files={"frame": ("f.jpg", b"x", "image/jpeg")},
    )
    assert r.status_code == 401
