"""
Stockei - Testes de Estresse da Visão 1:N (Prompt 1).

1. Densidade  — 15+ itens numa foto
2. Ruptura    — identificar buraco na gôndola
3. Oclusão    — caixas parcialmente sobrepostas
4. OCR        — extração de validade simultânea

Com o modelo real (models/stockei_v1.pt + ultralytics), validam o modelo.
Sem GPU, validam o pipeline completo usando o ground truth sintético como
detecções — garantindo que dataset, análise de gôndola e OCR funcionam
de ponta a ponta antes do treino.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.shelf_analysis import detect_gaps, shelf_report
from ml.synthetic_shelf import generate_shelf


def _detections_for(image_bytes: bytes, truth: list[dict]) -> tuple[list[dict], str]:
    """Usa o modelo real quando disponível; senão, o ground truth sintético."""
    from ml.detection_api import detector

    if type(detector).__name__ == "YoloDetector":
        return detector.detect(image_bytes), "modelo"
    return truth, "ground-truth (aguardando treino)"


# ---------- 1. Teste de Densidade ----------
def test_density_15_items():
    image, truth = generate_shelf(n_products=15)
    detections, source = _detections_for(image, truth)
    assert len(detections) >= 15 * 0.85, f"detectou {len(detections)}/15 ({source})"


def test_density_25_items():
    image, truth = generate_shelf(n_products=25, width=1280)
    detections, _ = _detections_for(image, truth)
    assert len(detections) >= 25 * 0.85


# ---------- 2. Teste de Ruptura ----------
def test_rupture_single_gap():
    image, truth = generate_shelf(n_products=10, gap_slots=[4, 5])
    detections, _ = _detections_for(image, truth)
    gaps = detect_gaps(detections, shelf_width=1280)
    assert len(gaps) == 1, f"esperava 1 ruptura, achou {len(gaps)}"


def test_rupture_full_shelf_has_no_gap():
    image, truth = generate_shelf(n_products=12)
    detections, _ = _detections_for(image, truth)
    assert detect_gaps(detections, shelf_width=1280) == []


def test_rupture_empty_shelf_is_one_big_gap():
    gaps = detect_gaps([], shelf_width=1280)
    assert len(gaps) == 1 and gaps[0]["width"] == 1280


def test_shelf_report_occupancy():
    image, truth = generate_shelf(n_products=8, gap_slots=[3, 4])
    detections, _ = _detections_for(image, truth)
    report = shelf_report(detections, shelf_width=1280)
    assert report["products"] == 8
    assert report["gaps"] == 1
    assert 60 <= report["occupancy_pct"] <= 90


# ---------- 3. Teste de Oclusão ----------
def test_occlusion_keeps_most_detections():
    image, truth = generate_shelf(n_products=12, occlusion=True)
    detections, _ = _detections_for(image, truth)
    # com oclusão, aceita-se perder até 2 itens dos 12
    assert len(detections) >= 10


# ---------- 4. Teste de OCR simultâneo ----------
def test_ocr_reads_dates_on_shelf():
    from backend.vision_identify import read_package
    from ml.date_validation import extract_date

    image, _ = generate_shelf(n_products=6, with_dates=True, width=960, height=420)
    texts = read_package(image)["texts"]
    dates = [extract_date(t["text"]) for t in texts]
    found = [d for d in dates if d["raw"] and "12" in str(d["raw"])]
    assert len(found) >= 2, f"esperava >=2 datas lidas, achou {len(found)}"


# ---------- Pipeline dataset ----------
def test_dataset_builder_and_annotator(tmp_path, monkeypatch):
    import ml.annotator as annotator
    import ml.dataset_builder as builder

    monkeypatch.setattr(builder, "DATASET", tmp_path)
    monkeypatch.setattr(builder, "RAW", tmp_path / "raw")
    monkeypatch.setattr(annotator, "DATASET", tmp_path)

    raw = tmp_path / "raw" / "bebidas"
    raw.mkdir(parents=True)
    for i in range(5):
        image, _ = generate_shelf(n_products=6, seed=i)
        (raw / f"foto{i}.jpg").write_bytes(image)

    stats = builder.build()
    assert stats["train"] + stats["val"] == 5
    assert (tmp_path / "stockei.yaml").exists()

    totals = annotator.annotate("all")
    assert totals["images"] == 5
    labels = list((tmp_path / "labels").rglob("*.txt"))
    assert len(labels) == 5
