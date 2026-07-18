"""
Stockei - Gerador de prateleiras sintéticas para os testes de estresse.
Cria imagens de gôndola com N produtos (caixas coloridas com rótulo e data),
buracos controlados e oclusão — e retorna o ground truth das caixas.
"""

import io
import random

from PIL import Image, ImageDraw, ImageFont

COLORS = ["#c0392b", "#2980b9", "#27ae60", "#f39c12", "#8e44ad", "#16a085"]


def _font(size):
    try:
        return ImageFont.truetype("arialbd.ttf", size)
    except OSError:
        return ImageFont.load_default()


def generate_shelf(
    n_products: int = 15,
    gap_slots: list[int] | None = None,
    occlusion: bool = False,
    with_dates: bool = False,
    width: int = 1280,
    height: int = 360,
    seed: int = 7,
) -> tuple[bytes, list[dict]]:
    """
    Gera uma prateleira com n_products distribuídos em slots; gap_slots ficam
    vazios (ruptura). Retorna (jpeg_bytes, ground_truth_boxes).
    """
    random.seed(seed)
    gap_slots = gap_slots or []
    total_slots = n_products + len(gap_slots)
    slot_w = width // total_slots

    img = Image.new("RGB", (width, height), "#d8d2c4")  # fundo de gôndola
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, height - 26, width, height], fill="#8a8272")  # trilho

    truth = []
    slot = 0
    placed = 0
    while placed < n_products:
        if slot in gap_slots:
            slot += 1
            continue
        x1 = slot * slot_w + 6
        x2 = (slot + 1) * slot_w - 6
        y1 = random.randint(46, 76)
        y2 = height - 30
        color = COLORS[placed % len(COLORS)]
        draw.rectangle([x1, y1, x2, y2], fill=color, outline="#222", width=2)
        draw.rectangle([x1 + 6, y1 + 12, x2 - 6, y1 + 44], fill="white")
        draw.text((x1 + 10, y1 + 16), f"P{placed + 1}", fill="#111", font=_font(22))
        if with_dates:
            draw.text((x1 + 8, y2 - 32), "VAL 12/2027", fill="white", font=_font(15))
        truth.append({"bbox": [float(x1), float(y1), float(x2), float(y2)],
                      "class_name": "produto", "confidence": 1.0})
        placed += 1
        slot += 1

    if occlusion and len(truth) >= 2:
        # sobrepõe uma caixa "caída" na frente de duas vizinhas
        b = truth[len(truth) // 2]["bbox"]
        draw.rectangle([b[0] - 30, b[3] - 90, b[2] + 30, b[3]],
                       fill="#555", outline="#111", width=2)

    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    return buf.getvalue(), truth
