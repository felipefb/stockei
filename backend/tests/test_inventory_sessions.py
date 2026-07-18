"""Stockei - Testes das sessões de inventário e posição de estoque (P16)."""

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
def ctx(client):
    client.post("/auth/register", json={
        "email": "inv@stockei.com", "password": "secret123", "name": "Inv"})
    token = client.post("/auth/login", json={
        "email": "inv@stockei.com", "password": "secret123"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    customer = client.post("/customers", headers=h, json={
        "name": "C", "cnpj": "22.222.222/0001-22", "email": "c@c.com"}).json()
    store = client.post("/stores", headers=h, json={
        "customer_id": customer["id"], "name": "Loja Inv"}).json()

    # 3 produtos com estoque 10/5/0
    for ean, name, qty in [("111", "Vigor Grego 90 g", 10),
                           ("222", "Coca-Cola 2 l", 5),
                           ("333", "Arroz 5 kg", 0)]:
        client.post(f"/identify/{ean}/register", headers=h,
                    json={"name": name, "store_id": store["id"]})
        if qty:
            client.post(f"/identify/{ean}/stock-in", headers=h, json={"quantity": qty})
    return {"h": h, "store_id": store["id"]}


def test_open_session_and_no_duplicates(client, ctx):
    r = client.post("/inventory/sessions", headers=ctx["h"],
                    json={"store_id": ctx["store_id"]})
    assert r.status_code == 201
    ctx["session_id"] = r.json()["id"]
    # segunda sessão aberta na mesma loja é bloqueada
    r = client.post("/inventory/sessions", headers=ctx["h"],
                    json={"store_id": ctx["store_id"]})
    assert r.status_code == 409


def test_record_counts(client, ctx):
    sid = ctx["session_id"]
    # 111: sistema 10, contado 8 (diff -2) · 222: 5=5 · 333: 0, contado 3 (+3)
    for ean, counted in [("111", 8), ("222", 5), ("333", 3)]:
        r = client.post(f"/inventory/sessions/{sid}/counts", headers=ctx["h"],
                        json={"ean": ean, "counted": counted})
        assert r.status_code == 200, r.text
    # recontagem sobrescreve (não duplica)
    client.post(f"/inventory/sessions/{sid}/counts", headers=ctx["h"],
                json={"ean": "111", "counted": 8})
    d = client.get(f"/inventory/sessions/{sid}", headers=ctx["h"]).json()
    assert d["total_items"] == 3
    assert d["divergent_items"] == 2


def test_count_unknown_ean(client, ctx):
    r = client.post(f"/inventory/sessions/{ctx['session_id']}/counts",
                    headers=ctx["h"], json={"ean": "999", "counted": 1})
    assert r.status_code == 404


def test_approve_applies_adjustments(client, ctx):
    sid = ctx["session_id"]
    r = client.post(f"/inventory/sessions/{sid}/approve", headers=ctx["h"])
    assert r.status_code == 200
    body = r.json()
    assert body["adjustments"] == 2                # 111 e 333
    assert body["accuracy_pct"] == pytest.approx(33.3, abs=0.1)

    # saldos ajustados
    inv = client.get("/inventory", headers=ctx["h"]).json()
    products = client.get("/products", headers=ctx["h"]).json()
    by_sku = {p["sku"]: p["id"] for p in products}
    qty = {i["product_id"]: i["quantity"] for i in inv}
    assert qty[by_sku["111"]] == 8
    assert qty[by_sku["222"]] == 5
    assert qty[by_sku["333"]] == 3

    # sessão fechada não aceita mais contagens
    r = client.post(f"/inventory/sessions/{sid}/counts", headers=ctx["h"],
                    json={"ean": "111", "counted": 1})
    assert r.status_code == 409


def test_discard_session(client, ctx):
    r = client.post("/inventory/sessions", headers=ctx["h"],
                    json={"store_id": ctx["store_id"]})
    sid = r.json()["id"]
    r = client.post(f"/inventory/sessions/{sid}/discard", headers=ctx["h"])
    assert r.json()["status"] == "discarded"


def test_position_current_and_historical(client, ctx):
    # posição atual reflete os ajustes aprovados
    pos = client.get(f"/inventory/position?store_id={ctx['store_id']}",
                     headers=ctx["h"]).json()
    assert pos["total_units"] == 8 + 5 + 3

    # posição em data futura (todos os movimentos incluídos no replay)
    pos = client.get(f"/inventory/position?date=2030-01-01&store_id={ctx['store_id']}",
                     headers=ctx["h"]).json()
    assert pos["total_units"] == 8 + 5 + 3

    # posição antes de qualquer movimento = zero
    pos = client.get(f"/inventory/position?date=2000-01-01&store_id={ctx['store_id']}",
                     headers=ctx["h"]).json()
    assert pos["total_units"] == 0

    # data inválida
    r = client.get("/inventory/position?date=01-01-2030", headers=ctx["h"])
    assert r.status_code == 422
