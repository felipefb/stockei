"""
Stockei - Benchmark de leitura de código de barras (zxing-cpp, servidor).

Roda sobre as imagens curadas do banco de códigos de barras (queries com
barra/barcode/ean, status=kept) e mede a taxa de decodificação em duas
condições: imagem original e com realce (mesmo enhance do OCR de datas).

Também serve de base para o fallback de servidor: quando o leitor do
navegador (iOS) falhar, o frame pode ser decodificado aqui.

Uso: python ml/benchmark_barcode.py
"""

import io
import json
from datetime import date
from pathlib import Path

SCRAPED = Path(__file__).parent / "dataset" / "scraped"
REPORT = Path(__file__).parent / "benchmark_barcode_report.md"

_BARCODE_HINTS = ("barra", "barcode", "ean")


def decode(image_bytes: bytes) -> str | None:
    """Decodifica o primeiro código 1D válido da imagem."""
    import zxingcpp
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    results = zxingcpp.read_barcodes(img)
    for r in results:
        text = r.text.strip()
        if text and len(text) >= 8:
            return text
    return None


def run() -> dict:
    from backend.vision_identify import enhance_for_ocr

    manifest = json.loads((SCRAPED / "manifest.json").read_text(encoding="utf-8"))
    cases = [f for f, m in manifest.items()
             if m.get("status") == "kept"
             and any(h in m.get("query", "").lower() for h in _BARCODE_HINTS)
             and (SCRAPED / f).exists()]
    if not cases:
        print("Nenhuma imagem de código de barras mantida — cure o banco primeiro.")
        return {}

    raw_ok = enh_ok = either = 0
    failures = []
    for fname in cases:
        data = (SCRAPED / fname).read_bytes()
        a = decode(data)
        b = None
        if a is None:
            try:
                b = decode(enhance_for_ocr(data))
            except Exception:
                pass
        raw_ok += a is not None
        enh_ok += b is not None
        if a or b:
            either += 1
        else:
            failures.append(fname)

    n = len(cases)
    lines = [
        "# Stockei — Benchmark de Código de Barras (zxing-cpp)",
        f"*Gerado em {date.today().isoformat()} · {n} imagens curadas*",
        "",
        "| Métrica | Resultado |",
        "|---|---|",
        f"| Decodificou (imagem original) | {raw_ok/n:.0%} |",
        f"| Recuperado pelo realce | {enh_ok/n:.0%} |",
        f"| Total decodificado | {either/n:.0%} |",
        "",
        "## Não decodificadas",
        "",
    ] + [f"- {f}" for f in failures]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"{n} imagens · original {raw_ok/n:.0%} · +realce {enh_ok/n:.0%} "
          f"· total {either/n:.0%}")
    print(f"Relatório: {REPORT}")
    return {"n": n, "raw": raw_ok / n, "total": either / n}


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    run()
