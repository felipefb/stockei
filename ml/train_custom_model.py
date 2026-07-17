"""
Stockei - Pipeline de treino do YOLOv8 customizado para produtos.

Uso (requer GPU + ultralytics + dataset anotado):
    python ml/train_custom_model.py --data ml/dataset/stockei.yaml --epochs 100

Dataset esperado (formato YOLO, anotado via Roboflow/LabelImg):
    ml/dataset/
      images/{train,val,test}/   # split 70/20/10
      labels/{train,val,test}/
      stockei.yaml
"""

import argparse
import json
from pathlib import Path

TRAIN_CONFIG = {
    "model": "yolov8m.pt",   # medium: melhor acurácia para produção
    "epochs": 100,
    "lr0": 0.001,
    "batch": 16,
    "imgsz": 640,
    "device": 0,             # GPU
    # Augmentation
    "hsv_h": 0.015, "hsv_s": 0.7, "hsv_v": 0.4,
    "fliplr": 0.5, "mosaic": 1.0, "scale": 0.5,
}

TARGETS = {"mAP50": 0.85, "recall": 0.85, "precision": 0.90}


def build_dataset_yaml(dataset_dir: Path, classes: list[str]) -> Path:
    """Gera o YAML de configuração do dataset no formato ultralytics."""
    yaml_path = dataset_dir / "stockei.yaml"
    lines = [
        f"path: {dataset_dir.resolve()}",
        "train: images/train",
        "val: images/val",
        "test: images/test",
        "names:",
    ]
    lines += [f"  {i}: {name}" for i, name in enumerate(classes)]
    yaml_path.write_text("\n".join(lines), encoding="utf-8")
    return yaml_path


def train(data_yaml: str, epochs: int, output_dir: str = "ml/runs") -> dict:
    from ultralytics import YOLO  # requer `pip install ultralytics`

    model = YOLO(TRAIN_CONFIG["model"])
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        lr0=TRAIN_CONFIG["lr0"],
        batch=TRAIN_CONFIG["batch"],
        imgsz=TRAIN_CONFIG["imgsz"],
        device=TRAIN_CONFIG["device"],
        project=output_dir,
        name="stockei_custom",
    )
    metrics = {
        "mAP50": float(results.box.map50),
        "mAP50-95": float(results.box.map),
        "precision": float(results.box.mp),
        "recall": float(results.box.mr),
    }
    return metrics


def validate_targets(metrics: dict) -> bool:
    ok = (
        metrics["mAP50"] >= TARGETS["mAP50"]
        and metrics["recall"] >= TARGETS["recall"]
        and metrics["precision"] >= TARGETS["precision"]
    )
    status = "APROVADO" if ok else "REPROVADO - retreinar com mais dados"
    print(f"Validação: {status} | {metrics}")
    return ok


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default="ml/dataset/stockei.yaml")
    parser.add_argument("--epochs", type=int, default=TRAIN_CONFIG["epochs"])
    args = parser.parse_args()

    metrics = train(args.data, args.epochs)
    Path("ml/metrics.json").write_text(json.dumps(metrics, indent=2))
    validate_targets(metrics)

    # exporta melhor checkpoint como modelo de produção
    best = Path("ml/runs/stockei_custom/weights/best.pt")
    if best.exists():
        best.replace("models/custom_model.pt")
        print("Modelo salvo em models/custom_model.pt")


if __name__ == "__main__":
    main()
