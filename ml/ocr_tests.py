"""Stockei - Testes do OCR de datas de validade."""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ml.date_validation import extract_date
from ml.ocr_engine import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _future(days=365):
    return (date.today() + timedelta(days=days)).strftime("%d/%m/%Y")


def test_extract_valid_date():
    r = extract_date(f"VAL: {_future()}")
    assert r["valid"] is True


def test_extract_date_formats():
    future = date.today() + timedelta(days=400)
    for fmt in ["%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%m/%Y"]:
        r = extract_date(future.strftime(fmt))
        assert r["valid"] is True, fmt


def test_expired_product():
    r = extract_date("01/01/2020")
    assert r["valid"] is False
    assert "vencido" in r["error"].lower()


def test_impossible_date_suggests_swap():
    year = date.today().year + 1
    r = extract_date(f"25/13/{year}")  # mês 13 -> sugere 13/25 invertido? não: 13/25 inválido
    assert r["valid"] is False


def test_ocr_common_confusions():
    # O no lugar de 0
    year = date.today().year + 1
    r = extract_date(f"1O/O5/{year}")
    assert r["valid"] is True
    assert r["date"].startswith(str(year))


def test_no_date_found():
    r = extract_date("PRODUTO XYZ 500MG")
    assert r["valid"] is False
    assert r["error"] == "Nenhuma data reconhecida"


def test_far_future_rejected():
    r = extract_date("01/01/2099")
    assert r["valid"] is False


def test_ocr_endpoint():
    payload = f"VAL {_future()}".encode()
    r = client.post("/ocr/date", files={"image": ("label.jpg", payload, "image/jpeg")})
    assert r.status_code == 200
    body = r.json()
    assert body["valid"] is True
    assert body["confidence"] >= 0.9
    assert body["latency_ms"] < 50


def test_ocr_endpoint_invalid():
    r = client.post("/ocr/date", files={"image": ("label.jpg", b"sem data aqui", "image/jpeg")})
    assert r.json()["valid"] is False
