"""Stockei - Testes do cadastro inteligente (preço + estoque mínimo por produto)."""

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
        "email": "smart@stockei.com", "password": "secret123", "name": "S"})
    token = client.post("/auth/login", json={
        "email": "smart@stockei.com", "password": "secret123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _inv_for(client, auth, ean):
    products = client.get("/products", headers=auth).json()
    pid = next(p["id"] for p in products if p["sku"] == ean)
    return next(i for i in client.get("/inventory", headers=auth).json()
                if i["product_id"] == pid)


def test_register_with_price_and_min(client, auth):
    r = client.post("/identify/100/register", headers=auth, json={
        "name": "Pelicula iPhone 16", "price": 43.62, "min_stock": 10})
    assert r.status_code == 201
    assert r.json()["product"]["price"] == 43.62
    assert _inv_for(client, auth, "100")["min_stock"] == 10


def test_register_min_defaults_by_category(client, auth):
    # Bebidas → padrão 12
    client.post("/identify/200/register", headers=auth,
                json={"name": "Coca-Cola Refrigerante 2 l"})
    assert _inv_for(client, auth, "200")["min_stock"] == 12
    # sem categoria reconhecida → padrão 5
    client.post("/identify/300/register", headers=auth,
                json={"name": "Produto Generico Sem Marca"})
    assert _inv_for(client, auth, "300")["min_stock"] == 5


def test_low_stock_uses_per_product_min(client, auth):
    # produto 100 (min 10): 8 unidades → em alerta mesmo acima do antigo limite 5
    for _ in range(8):
        client.post("/identify/100/stock-in", json={"quantity": 1}, headers=auth)
    d = client.get("/dashboard/summary", headers=auth).json()
    alert = next((i for i in d["low_stock"] if i["sku"] == "100"), None)
    assert alert is not None
    assert alert["quantity"] == 8 and alert["min_stock"] == 10

    # subiu para 10 → sai do alerta
    for _ in range(2):
        client.post("/identify/100/stock-in", json={"quantity": 1}, headers=auth)
    d = client.get("/dashboard/summary", headers=auth).json()
    assert all(i["sku"] != "100" for i in d["low_stock"])


def test_csv_includes_min_stock(client, auth):
    r = client.get("/inventory/export.csv", headers=auth)
    header = r.content.decode("utf-8-sig").splitlines()[0]
    assert "estoque_minimo" in header
