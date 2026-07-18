"""
Stockei - Análise de gôndola: detecção de rupturas (buracos) a partir das
detecções de produtos. Um buraco é um vão horizontal entre produtos vizinhos
na mesma faixa vertical, maior que a largura média de um produto.
"""

GAP_FACTOR = 0.8  # vão >= 80% da largura média de produto = ruptura


def detect_gaps(detections: list[dict], shelf_width: float) -> list[dict]:
    """
    detections: [{bbox: [x1,y1,x2,y2], ...}] de UMA prateleira (faixa horizontal).
    Retorna [{x_start, x_end, width}] com os vãos encontrados.
    """
    if not detections:
        if shelf_width > 0:
            return [{"x_start": 0.0, "x_end": shelf_width, "width": shelf_width}]
        return []

    boxes = sorted((d["bbox"] for d in detections), key=lambda b: b[0])
    avg_width = sum(b[2] - b[0] for b in boxes) / len(boxes)
    threshold = avg_width * GAP_FACTOR

    gaps = []
    cursor = 0.0
    for box in boxes:
        if box[0] - cursor >= threshold:
            gaps.append({"x_start": cursor, "x_end": box[0], "width": box[0] - cursor})
        cursor = max(cursor, box[2])
    if shelf_width - cursor >= threshold:
        gaps.append({"x_start": cursor, "x_end": shelf_width,
                     "width": shelf_width - cursor})
    return gaps


def shelf_report(detections: list[dict], shelf_width: float) -> dict:
    """Resumo de ocupação da prateleira para o dashboard."""
    gaps = detect_gaps(detections, shelf_width)
    gap_total = sum(g["width"] for g in gaps)
    return {
        "products": len(detections),
        "gaps": len(gaps),
        "gap_width_total": round(gap_total, 1),
        "occupancy_pct": round(100 * (1 - gap_total / shelf_width), 1)
        if shelf_width else 0.0,
    }
