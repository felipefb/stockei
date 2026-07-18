"""
Stockei - Anotador automático do dataset.

Para cada imagem em ml/dataset/images/{train,val}, gera:
- label YOLO (.txt) em ml/dataset/labels/{split}/ usando o detector atual
  (YOLOv8 pré-treinado quando instalado; MockDetector marca para revisão);
- sidecar .meta.json com datas de validade lidas por OCR (RapidOCR).

As anotações automáticas são PONTO DE PARTIDA: revisar no Roboflow/LabelImg
antes do treino (especialmente a classe "ruptura", que é manual).

Uso: python ml/annotator.py [--split train|val|all]
"""

import argparse
import json
from pathlib import Path

DATASET = Path(__file__).parent / "dataset"


def _to_yolo_line(class_id: int, bbox, img_w: int, img_h: int) -> str:
    """Converte bbox [x1,y1,x2,y2] absoluto para o formato YOLO normalizado."""
    x1, y1, x2, y2 = bbox
    cx = ((x1 + x2) / 2) / img_w
    cy = ((y1 + y2) / 2) / img_h
    w = (x2 - x1) / img_w
    h = (y2 - y1) / img_h
    return f"{class_id} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}"


def annotate_image(image_path: Path, labels_dir: Path) -> dict:
    """Anota uma imagem: detecções → label YOLO; OCR → sidecar de validade."""
    from PIL import Image

    from ml.detection_api import detector

    data = image_path.read_bytes()
    img_w, img_h = Image.open(image_path).size

    detections = detector.detect(data)
    lines = [
        _to_yolo_line(0, det["bbox"], img_w, img_h)  # classe 0 = produto
        for det in detections
        if det["bbox"][2] <= img_w and det["bbox"][3] <= img_h
    ]
    label_path = labels_dir / (image_path.stem + ".txt")
    label_path.write_text("\n".join(lines), encoding="utf-8")

    # OCR de datas de validade (opcional — segue sem se indisponível)
    expiry_dates = []
    try:
        from backend.vision_identify import read_package
        from ml.date_validation import extract_date

        for t in read_package(data)["texts"]:
            result = extract_date(t["text"])
            if result["valid"]:
                expiry_dates.append(result["date"])
    except Exception:
        pass

    meta = {
        "detections": len(lines),
        "detector": type(detector).__name__,
        "needs_review": type(detector).__name__ == "MockDetector",
        "expiry_dates": expiry_dates,
    }
    (labels_dir / (image_path.stem + ".meta.json")).write_text(
        json.dumps(meta), encoding="utf-8"
    )
    return meta


def annotate(split: str = "all") -> dict:
    splits = ["train", "val"] if split == "all" else [split]
    totals = {"images": 0, "boxes": 0, "with_expiry": 0, "needs_review": 0}
    for s in splits:
        images_dir = DATASET / "images" / s
        labels_dir = DATASET / "labels" / s
        labels_dir.mkdir(parents=True, exist_ok=True)
        for image_path in sorted(images_dir.glob("*.jpg")):
            meta = annotate_image(image_path, labels_dir)
            totals["images"] += 1
            totals["boxes"] += meta["detections"]
            totals["with_expiry"] += bool(meta["expiry_dates"])
            totals["needs_review"] += meta["needs_review"]
    print(f"Anotadas {totals['images']} imagens, {totals['boxes']} caixas, "
          f"{totals['with_expiry']} com validade lida; "
          f"{totals['needs_review']} marcadas para revisão manual.")
    return totals


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="all", choices=["train", "val", "all"])
    annotate(parser.parse_args().split)
