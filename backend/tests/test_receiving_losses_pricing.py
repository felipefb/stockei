"""Stockei - Testes de recebimento NF-e (P10), perdas (P11) e pricing (P5)."""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_stockei.db")

import pytest
from fastapi.testclient import TestClient

from backend.app import _rate_state, app
from backend.database import Base, engine

NFE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">
 <NFe>
  <infNFe Id="NFe35260707000000000000550010000000011000000010" versao="4.00">
   <ide><dhEmi>2026-07-20T10:00:00-03:00</dhEmi></ide>
   <emit><xNome>Distribuidora Boa Vista LTDA</xNome></emit>
   <det nItem="1"><prod>
     <cEAN>7891000100103</cEAN><xProd>LEITE COND MOCA 395G</xProd>
     <qCom>10.0000</qCom><vUnCom>6.5000</vUnCom>
   </prod></det>
   <det nItem="2"><prod>
     <cEAN>7894900011517</cEAN><xProd>COCA COLA 2L</xProd>
     <qCom>6.0000</qCom><vUnCom>7.9000</vUnCom>
   </prod></det>
   <det nItem="3"><prod>
     <cEAN>SEM GTIN</cEAN><cEANTrib>SEM GTIN</cEANTrib>
     <xProd>CAIXA PAPELAO</xProd><qCom>1.0000</qCom><vUnCom>2.0000</vUnCom>
   </prod></det>
  </infNFe>
 </NFe>
</nfeProc>"""


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
        "email": "recv@stockei.com", "password": "secret123", "name": "Recv"})
    token = client.post("/auth/login", json={
        "email": "recv@stockei.com", "password": "secret123"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    customer = client.post("/customers", headers=h, json={
        "name": "C", "cnpj": "33.333.333/0001-33", "email": "c@c.com"}).json()
    store = client.post("/stores", headers=h, json={
        "customer_id": customer["id"], "name": "Loja Recv"}).json()
    return {"h": h, "store_id": store["id"]}


# ---------- P10: recebimento ----------
def _upload(client, ctx):
    return client.post(f"/receiving/upload-xml?store_id={ctx['store_id']}",
                       headers=ctx["h"],
                       files={"xml": ("nota.xml", NFE_XML, "text/xml")})


def test_upload_xml_creates_session(client, ctx):
    r = _upload(client, ctx)
    assert r.status_code == 201, r.text
    d = r.json()
    ctx["recv_id"] = d["id"]
    assert d["supplier"] == "Distribuidora Boa Vista LTDA"
    assert d["total_items"] == 3
    assert d["total_value"] == round(10 * 6.5 + 6 * 7.9 + 2.0, 2)
    eans = {i["ean"] for i in d["items"]}
    assert "7891000100103" in eans and "" in eans  # SEM GTIN vira ean vazio


def test_duplicate_nfe_blocked(client, ctx):
    assert _upload(client, ctx).status_code == 409


def test_invalid_xml_rejected(client, ctx):
    r = client.post("/receiving/upload-xml", headers=ctx["h"],
                    files={"xml": ("x.xml", "<foo/>", "text/xml")})
    assert r.status_code == 422


def test_check_flow_and_close(client, ctx):
    h, rid = ctx["h"], ctx["recv_id"]
    # leite: confere as 10 (em duas bipadas de 5)
    for _ in range(2):
        r = client.post(f"/receiving/{rid}/check", headers=h,
                        json={"ean": "7891000100103", "qty": 5})
    assert r.json()["status"] == "conferido"
    # coca: só 4 de 6 → divergente
    r = client.post(f"/receiving/{rid}/check", headers=h,
                    json={"ean": "7894900011517", "qty": 4})
    assert r.json()["status"] == "divergente"
    # excedente: veio um produto fora da nota
    r = client.post(f"/receiving/{rid}/check", headers=h,
                    json={"ean": "7891910000197", "qty": 2})
    assert r.json()["status"] == "excedente"

    r = client.post(f"/receiving/{rid}/close", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["entered_units"] == 10 + 4 + 2
    # produtos da nota não existiam: cadastro automático (leite, coca, excedente)
    assert len(d["auto_registered"]) == 3
    # divergência da coca reportada
    assert any(v["ean"] == "7894900011517" and v["status"] == "faltou"
               for v in d["divergences"])

    # estoque refletiu a conferência e o custo da nota alimentou o produto
    r = client.get("/identify/7891000100103", headers=h).json()
    assert r["quantity"] == 10
    assert r["product"]["cost_price"] == 6.5


def test_closed_session_rejects_check(client, ctx):
    r = client.post(f"/receiving/{ctx['recv_id']}/check", headers=ctx["h"],
                    json={"ean": "7891000100103"})
    assert r.status_code == 409


# ---------- P11: perdas ----------
def test_loss_requires_valid_reason(client, ctx):
    r = client.post("/losses", headers=ctx["h"],
                    json={"ean": "7891000100103", "quantity": 1, "reason": "clima"})
    assert r.status_code == 422


def test_loss_lowers_stock_and_values(client, ctx):
    h = ctx["h"]
    # dá preço de venda ao leite para valorizar a perda
    client.post("/pricing/7891000100103/apply", headers=h, json={"price": 9.0})
    r = client.post("/losses", headers=h, json={
        "ean": "7891000100103", "quantity": 2, "reason": "avaria",
        "note": "caixa amassada"})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["value"] == 18.0
    assert d["stock_after"] == 8

    report = client.get("/losses/report?days=30", headers=h).json()
    assert report["total_units"] == 2
    assert report["total_value"] == 18.0
    assert report["by_reason"][0]["reason"] == "avaria"
    assert report["loss_pct_of_stock"] is not None


def test_loss_appears_in_dashboard(client, ctx):
    d = client.get("/dashboard/summary", headers=ctx["h"]).json()
    assert d["losses_30d"] == 18.0


# ---------- P5: pricing ----------
def test_margin_suggestion_from_nfe_cost(client, ctx):
    h = ctx["h"]
    # coca custou 7.90 e está sem preço de venda → sugestão de margem
    d = client.get("/pricing/suggestions", headers=h).json()
    coca = next(s for s in d["suggestions"] if s["sku"] == "7894900011517")
    assert coca["type"] == "margem"
    assert coca["suggested_price"] > 7.9  # acima do custo


def test_expiry_discount_never_below_cost(client, ctx):
    h = ctx["h"]
    # leite vence em 5 dias → faixa -50%, mas nunca abaixo do custo (6.50)
    soon = (datetime.utcnow() + timedelta(days=5)).date().isoformat()
    client.post("/identify/7891000100103/expiry", headers=h,
                json={"expiry_date": soon})
    d = client.get("/pricing/suggestions", headers=h).json()
    leite = next(s for s in d["suggestions"] if s["sku"] == "7891000100103")
    assert leite["type"] == "validade"
    assert leite["discount_pct"] == 50
    # 9.00 * 0.5 = 4.50 < custo 6.50 → trava no custo
    assert leite["suggested_price"] == 6.5
    assert leite["floored_at_cost"] is True


def test_apply_price(client, ctx):
    r = client.post("/pricing/7894900011517/apply", headers=ctx["h"],
                    json={"price": 10.9})
    assert r.status_code == 200
    assert r.json()["price"] == 10.9
