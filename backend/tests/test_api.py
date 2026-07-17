"""Stockei - Testes das APIs base (auth, CRUD, inventário, movimentações)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ["DATABASE_URL"] = "sqlite:///./test_stockei.db"

import pytest
from fastapi.testclient import TestClient

from backend.app import app
from backend.database import Base, engine


@pytest.fixture(scope="module")
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_stockei.db"):
        try:
            engine.dispose()
            os.remove("test_stockei.db")
        except OSError:
            pass


@pytest.fixture(scope="module")
def auth_headers(client):
    client.post(
        "/auth/register",
        json={"email": "admin@stockei.com", "password": "secret123", "name": "Admin"},
    )
    resp = client.post(
        "/auth/login", json={"email": "admin@stockei.com", "password": "secret123"}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    assert client.get("/health").status_code == 200


def test_register_and_login(client):
    r = client.post(
        "/auth/register",
        json={"email": "user@stockei.com", "password": "password1", "name": "User"},
    )
    assert r.status_code == 201
    # email duplicado
    r = client.post(
        "/auth/register",
        json={"email": "user@stockei.com", "password": "password1", "name": "User"},
    )
    assert r.status_code == 409
    # login ok
    r = client.post("/auth/login", json={"email": "user@stockei.com", "password": "password1"})
    assert r.status_code == 200
    assert "access_token" in r.json()
    # login senha errada
    r = client.post("/auth/login", json={"email": "user@stockei.com", "password": "wrong9999"})
    assert r.status_code == 401


def test_refresh_token(client):
    r = client.post("/auth/login", json={"email": "user@stockei.com", "password": "password1"})
    refresh = r.json()["refresh_token"]
    r = client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    r = client.post("/auth/refresh", json={"refresh_token": "invalid.token.here"})
    assert r.status_code == 401


def test_protected_route_requires_auth(client):
    assert client.get("/users/me").status_code == 401
    assert client.get("/customers").status_code == 401


def test_users_me(client, auth_headers):
    r = client.get("/users/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["email"] == "admin@stockei.com"
    r = client.put("/users/me", json={"name": "Admin Updated"}, headers=auth_headers)
    assert r.json()["name"] == "Admin Updated"


def test_customer_store_camera_crud(client, auth_headers):
    r = client.post(
        "/customers",
        json={"name": "Farmácia Central", "cnpj": "11.222.333/0001-44", "email": "c@f.com"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    customer_id = r.json()["id"]

    r = client.post(
        "/stores",
        json={"customer_id": customer_id, "name": "Loja 1", "city": "São Paulo", "state": "SP"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    store_id = r.json()["id"]

    r = client.post(
        "/cameras",
        json={"store_id": store_id, "name": "Cam Entrada", "location": "Entrada"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["status"] == "offline"

    assert len(client.get("/customers", headers=auth_headers).json()) == 1
    assert client.get(f"/stores/{store_id}", headers=auth_headers).status_code == 200
    assert client.get("/stores/9999", headers=auth_headers).status_code == 404


def test_product_inventory_movements(client, auth_headers):
    store_id = client.get("/stores", headers=auth_headers).json()[0]["id"]

    r = client.post(
        "/products",
        json={"store_id": store_id, "sku": "SKU-001", "name": "Dipirona 500mg", "price": 9.9},
        headers=auth_headers,
    )
    assert r.status_code == 201
    product_id = r.json()["id"]

    # inventário criado automaticamente com o produto
    inv = client.get("/inventory", headers=auth_headers).json()
    assert any(i["product_id"] == product_id for i in inv)

    # movimento de entrada atualiza o estoque
    r = client.post(
        "/movements",
        json={"product_id": product_id, "quantity": 10, "type": "in"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    inv = [i for i in client.get("/inventory", headers=auth_headers).json() if i["product_id"] == product_id][0]
    assert inv["quantity"] == 10

    # saída
    client.post(
        "/movements",
        json={"product_id": product_id, "quantity": 3, "type": "out"},
        headers=auth_headers,
    )
    inv = [i for i in client.get("/inventory", headers=auth_headers).json() if i["product_id"] == product_id][0]
    assert inv["quantity"] == 7

    # contagem manual
    r = client.post(
        "/inventory/count",
        json={"product_id": product_id, "quantity": 6},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["quantity"] == 6
    assert r.json()["last_count"] == 7

    # tipo inválido rejeitado pelo Pydantic
    r = client.post(
        "/movements",
        json={"product_id": product_id, "quantity": 1, "type": "steal"},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_invalid_token_rejected(client):
    r = client.get("/users/me", headers={"Authorization": "Bearer abc.def.ghi"})
    assert r.status_code == 401
