"""Stockei - Testes do dashboard de estoque."""

import os
import sys

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
        "email": "dash@stockei.com", "password": "secret123", "name": "Dash"})
    token = client.post("/auth/login", json={
        "email": "dash@stockei.com", "password": "secret123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_empty(client, auth):
    d = client.get("/dashboard/summary", headers=auth).json()
    assert d["total_products"] == 0
    assert d["stock_value"] == 0
    assert d["recent_movements"] == []


def test_dashboard_with_stock(client, auth):
    # cadastra via EAN e movimenta
    client.post("/identify/111/register",
                json={"name": "Vigor Grego 90 g", "source": "ocr"}, headers=auth)
    client.post("/identify/222/register",
                json={"name": "Coca-Cola Refrigerante 2 l"}, headers=auth)
    for _ in range(6):
        client.post("/identify/111/stock-in", json={"quantity": 1}, headers=auth)

    # define preço do produto 111
    products = client.get("/products", headers=auth).json()
    p1 = next(p for p in products if p["sku"] == "111")
    client.put(f"/products/{p1['id']}", headers=auth, json={
        "store_id": p1["store_id"], "sku": "111", "name": p1["name"],
        "category": p1["category"], "price": 5.0})

    d = client.get("/dashboard/summary", headers=auth).json()
    assert d["total_products"] == 2
    assert d["total_units"] == 6
    assert d["stock_value"] == 30.0                      # 6 un x R$5
    # minimos por categoria: 111 Laticinios (min 8, qty 6) e 222 Bebidas (min 12, qty 0)
    assert {i["sku"] for i in d["low_stock"]} == {"111", "222"}
    cats = {c["category"] for c in d["by_category"]}
    assert "Laticínios" in cats
    assert len(d["recent_movements"]) == 6
    assert d["recent_movements"][0]["type"] == "in"


def test_dashboard_requires_auth(client):
    assert client.get("/dashboard/summary").status_code == 401
