"""Stockei - Testes da identificação por código de barras (EAN)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_stockei.db")

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.database import Base, engine

EAN = "7891025301453"  # exemplo de EAN-13


@pytest.fixture(scope="module")
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def auth(client):
    client.post("/auth/register", json={
        "email": "scan@stockei.com", "password": "secret123", "name": "Scanner"})
    token = client.post("/auth/login", json={
        "email": "scan@stockei.com", "password": "secret123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_identify_unknown_ean(client, auth):
    r = client.get(f"/identify/{EAN}", headers=auth)
    assert r.status_code == 200
    assert r.json()["found"] is False


def test_register_by_ean(client, auth):
    r = client.post(f"/identify/{EAN}/register",
                    json={"name": "Vigor Grego Tradicional 90g"}, headers=auth)
    assert r.status_code == 201
    body = r.json()
    assert body["product"]["name"] == "Vigor Grego Tradicional 90g"
    assert body["quantity"] == 0
    # duplicado
    r = client.post(f"/identify/{EAN}/register", json={"name": "X"}, headers=auth)
    assert r.status_code == 409


def test_identify_found_after_register(client, auth):
    r = client.get(f"/identify/{EAN}", headers=auth)
    body = r.json()
    assert body["found"] is True
    assert body["product"]["sku"] == EAN


def test_stock_in(client, auth):
    for expected in (1, 2, 3):
        r = client.post(f"/identify/{EAN}/stock-in", json={"quantity": 1}, headers=auth)
        assert r.status_code == 200
        assert r.json()["quantity"] == expected
    # movimentação registrada no histórico
    movements = client.get("/movements", headers=auth).json()
    assert len([m for m in movements if m["type"] == "in"]) == 3


def test_stock_in_unknown_ean(client, auth):
    r = client.post("/identify/000000/stock-in", json={"quantity": 1}, headers=auth)
    assert r.status_code == 404


def test_identify_requires_auth(client):
    assert client.get(f"/identify/{EAN}").status_code == 401
