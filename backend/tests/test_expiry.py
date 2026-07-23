"""Stockei - Testes do controle de validade."""

import io
import os
import sys
from datetime import date, datetime, timedelta

# o servidor calcula days_left com utcnow(); à noite (UTC-3) o
# _TODAY local fica um dia atrás e o teste quebrava
_TODAY = datetime.utcnow().date()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_stockei.db")

import pytest
from fastapi.testclient import TestClient

from backend.app import _rate_state, app
from backend.database import Base, engine

EAN = "7891999012345"


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
        "email": "exp@stockei.com", "password": "secret123", "name": "Exp"})
    token = client.post("/auth/login", json={
        "email": "exp@stockei.com", "password": "secret123"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    client.post(f"/identify/{EAN}/register", json={"name": "Vigor Grego 90 g"}, headers=h)
    client.post(f"/identify/{EAN}/stock-in", json={"quantity": 10}, headers=h)
    return h


def _label_with_date(text):
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (640, 200), "white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 48)
    except OSError:
        font = ImageFont.load_default()
    draw.text((30, 60), text, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_set_expiry(client, auth):
    future = (_TODAY + timedelta(days=20)).isoformat()
    r = client.post(f"/identify/{EAN}/expiry", json={"expiry_date": future}, headers=auth)
    assert r.status_code == 200
    assert r.json()["days_left"] == 20


def test_set_expiry_invalid_date(client, auth):
    r = client.post(f"/identify/{EAN}/expiry", json={"expiry_date": "31-12-2027"}, headers=auth)
    assert r.status_code == 422


def test_set_expiry_unknown_product(client, auth):
    r = client.post("/identify/000/expiry", json={"expiry_date": "2027-01-01"}, headers=auth)
    assert r.status_code == 404


def test_dashboard_shows_expiring(client, auth):
    d = client.get("/dashboard/summary", headers=auth).json()
    assert len(d["expiring"]) == 1
    item = d["expiring"][0]
    assert item["sku"] == EAN
    assert item["days_left"] == 20
    assert d["expiring_value"] == item["value"]


def test_dashboard_ignores_far_expiry(client, auth):
    far = (_TODAY + timedelta(days=200)).isoformat()
    client.post(f"/identify/{EAN}/expiry", json={"expiry_date": far}, headers=auth)
    d = client.get("/dashboard/summary", headers=auth).json()
    assert d["expiring"] == []


def test_expiry_from_image(client, auth):
    future = (_TODAY + timedelta(days=300)).strftime("%d/%m/%Y")
    r = client.post(
        "/identify/expiry-from-image",
        files={"frame": ("f.jpg", _label_with_date(f"VAL {future}"), "image/jpeg")},
        headers=auth,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    assert body["date"] is not None


def test_expiry_from_image_no_date(client, auth):
    r = client.post(
        "/identify/expiry-from-image",
        files={"frame": ("f.jpg", _label_with_date("PRODUTO SEM DATA"), "image/jpeg")},
        headers=auth,
    )
    assert r.json()["valid"] is False
