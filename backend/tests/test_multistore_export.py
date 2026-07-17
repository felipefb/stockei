"""Stockei - Testes de multi-loja e export CSV do inventário."""

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
        "email": "multi@stockei.com", "password": "secret123", "name": "Multi"})
    token = client.post("/auth/login", json={
        "email": "multi@stockei.com", "password": "secret123"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def stores(client, auth):
    customer = client.post("/customers", headers=auth, json={
        "name": "Rede Demo", "cnpj": "11.111.111/0001-11", "email": "r@d.com"}).json()
    a = client.post("/stores", headers=auth, json={
        "customer_id": customer["id"], "name": "Loja A", "city": "SP"}).json()
    b = client.post("/stores", headers=auth, json={
        "customer_id": customer["id"], "name": "Loja B", "city": "RJ"}).json()
    return a, b


def test_register_ean_in_specific_store(client, auth, stores):
    store_a, store_b = stores
    r = client.post("/identify/111/register", headers=auth, json={
        "name": "Vigor Grego 90 g", "source": "ocr", "store_id": store_a["id"]})
    assert r.status_code == 201
    assert r.json()["product"]["store_id"] == store_a["id"]

    r = client.post("/identify/222/register", headers=auth, json={
        "name": "Coca-Cola Refrigerante 2 l", "store_id": store_b["id"]})
    assert r.json()["product"]["store_id"] == store_b["id"]

    # loja inexistente
    r = client.post("/identify/333/register", headers=auth, json={
        "name": "X", "store_id": 9999})
    assert r.status_code == 404


def test_dashboard_filters_by_store(client, auth, stores):
    store_a, store_b = stores
    for _ in range(5):
        client.post("/identify/111/stock-in", json={"quantity": 1}, headers=auth)

    all_stores = client.get("/dashboard/summary", headers=auth).json()
    only_a = client.get(f"/dashboard/summary?store_id={store_a['id']}", headers=auth).json()
    only_b = client.get(f"/dashboard/summary?store_id={store_b['id']}", headers=auth).json()

    assert all_stores["total_products"] == 2
    assert only_a["total_products"] == 1
    assert only_a["total_units"] == 5
    assert only_b["total_units"] == 0
    assert all(m["product"].startswith("Vigor") for m in only_a["recent_movements"])


def test_export_csv(client, auth, stores):
    store_a, _ = stores
    r = client.get("/inventory/export.csv", headers=auth)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "attachment" in r.headers["content-disposition"]
    body = r.content.decode("utf-8-sig")
    lines = body.strip().splitlines()
    assert lines[0].startswith("loja;ean;produto")
    assert len(lines) == 3  # cabecalho + 2 produtos

    # filtrado por loja
    r = client.get(f"/inventory/export.csv?store_id={store_a['id']}", headers=auth)
    lines = r.content.decode("utf-8-sig").strip().splitlines()
    assert len(lines) == 2
    assert "Loja A" in lines[1]
    assert "111" in lines[1]


def test_export_requires_auth(client):
    assert client.get("/inventory/export.csv").status_code == 401
