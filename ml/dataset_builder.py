"""
Stockei - Construtor do dataset YOLOv8 (Visão 1:N).

Organiza fotos reais de prateleiras em um dataset pronto para treino:
valida, normaliza (máx. 1280px), divide train/val 80/20 e gera o YAML.

Uso:
  1. Jogue as fotos em ml/dataset/raw/<categoria>/  (ex.: medicamentos, higiene,
     bebidas, mercearia) — fotos de PRATELEIRAS CHEIAS, não produtos isolados.
  2. python ml/dataset_builder.py            → monta train/val + stockei.yaml
  3. python ml/annotator.py                  → gera labels automáticos (revisar!)
  4. Treino: ver docs/treino_colab.md (GPU gratuita) ou ml/train_custom_model.py
"""

import argparse
import hashlib
import random
import shutil
import sys
from pathlib import Path

DATASET = Path(__file__).parent / "dataset"
RAW = DATASET / "raw"
MAX_SIDE = 1280
VAL_SPLIT = 0.2
MIN_PER_CATEGORY = 50  # meta do Prompt 1

CLASSES = ["produto", "ruptura"]  # ruptura = buraco de gôndola (anotação manual)


def _normalize(src: Path, dst: Path) -> bool:
    """Valida e normaliza uma imagem; retorna False se inválida."""
    from PIL import Image

    try:
        img = Image.open(src)
        img.verify()
        img = Image.open(src).convert("RGB")
    except Exception:
        return False
    if max(img.size) > MAX_SIDE:
        ratio = MAX_SIDE / max(img.size)
        img = img.resize((int(img.width * ratio), int(img.height * ratio)))
    img.save(dst, "JPEG", quality=92)
    return True


def build(seed: int = 42) -> dict:
    """Monta o dataset a partir de ml/dataset/raw/<categoria>/*."""
    random.seed(seed)
    stats: dict = {"categories": {}, "train": 0, "val": 0, "invalid": 0}

    images = []
    for cat_dir in sorted(RAW.glob("*")):
        if not cat_dir.is_dir():
            continue
        files = [f for f in cat_dir.iterdir()
                 if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
        stats["categories"][cat_dir.name] = len(files)
        images += [(cat_dir.name, f) for f in files]

    if not images:
        print(f"Nenhuma imagem em {RAW}/<categoria>/ — adicione fotos de prateleiras.")
        return stats

    random.shuffle(images)
    n_val = max(1, int(len(images) * VAL_SPLIT))

    for split in ("train", "val"):
        (DATASET / "images" / split).mkdir(parents=True, exist_ok=True)
        (DATASET / "labels" / split).mkdir(parents=True, exist_ok=True)

    for i, (cat, src) in enumerate(images):
        split = "val" if i < n_val else "train"
        digest = hashlib.md5(src.read_bytes()).hexdigest()[:10]
        dst = DATASET / "images" / split / f"{cat}_{digest}.jpg"
        if _normalize(src, dst):
            stats[split] += 1
        else:
            stats["invalid"] += 1

    yaml_path = DATASET / "stockei.yaml"
    lines = [f"path: {DATASET.resolve()}", "train: images/train", "val: images/val",
             "names:"] + [f"  {i}: {n}" for i, n in enumerate(CLASSES)]
    yaml_path.write_text("\n".join(lines), encoding="utf-8")

    print(f"Dataset: {stats['train']} treino / {stats['val']} validação "
          f"({stats['invalid']} inválidas) → {yaml_path}")
    for cat, count in stats["categories"].items():
        flag = "OK" if count >= MIN_PER_CATEGORY else f"faltam {MIN_PER_CATEGORY - count}"
        print(f"  {cat}: {count} imagens [{flag}]")
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    sys.exit(0 if build(args.seed)["train"] > 0 else 1)
