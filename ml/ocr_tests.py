"""Stockei - Testes do OCR de datas de validade."""

import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ml.date_validation import extract_best_expiry, extract_date
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


def test_metal_stamp_mm_yy():
    """Gravação em metal: '12 26' e '12/26' = dezembro/2026, fim do mês."""
    for raw in ["12 26", "12/26", "VAL 12.26"]:
        r = extract_date(raw)
        assert r["valid"] is True, raw
        assert r["date"] == "2026-12-31", raw


def test_metal_stamp_expired_mm_yy_still_extracts_date():
    """'05 26' já venceu (estamos depois de mai/26): data extraída + flag."""
    r = extract_date("05 26")
    assert r["valid"] is False
    assert r["date"] == "2026-05-31"
    assert "vencido" in r["error"].lower()


def test_metal_stamp_with_lot_number():
    """Linha real de lata: lote + data — o lote não pode virar data."""
    r = extract_date("L 407004604 12 26 L31")
    assert r["valid"] is True
    assert r["date"] == "2026-12-31"


def test_spaced_dd_mm_yy():
    r = extract_date("15 08 26")
    assert r["valid"] is True
    assert r["date"] == "2026-08-15"


def test_implausible_short_pairs_are_not_dates():
    # mês 46 e ano fora da janela não são datas
    for raw in ["46 04", "13 99", "00 12"]:
        r = extract_date(raw)
        assert r["valid"] is False, raw


def test_prefers_validity_over_fabrication():
    """Linha com FAB e VAL — deve escolher a validade, não a fabricação."""
    r = extract_best_expiry("F 01/04/25 V 01/04/27")
    assert r["date"] == "2027-04-01"
    r = extract_best_expiry("FAB 15/08/24 VAL 15/08/26")
    assert r["date"] == "2026-08-15"
    r = extract_best_expiry("FABR 10/2025 VENC 10/2027")
    assert r["date"] == "2027-10-31"


def test_two_dates_no_label_picks_latest():
    """Sem rótulo, a validade é a data mais distante no futuro."""
    r = extract_best_expiry("01/04/25 01/04/27")
    assert r["date"] == "2027-04-01"


def test_full_date_not_shadowed_by_mm_yy():
    """15/08/26 não pode virar 08/26 (fim do mês) — dia é preservado."""
    r = extract_best_expiry("VAL 15/08/26")
    assert r["date"] == "2026-08-15"


def test_single_date_still_works():
    r = extract_best_expiry("L J35MD002 08/27")
    assert r["date"] == "2027-08-31"


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
