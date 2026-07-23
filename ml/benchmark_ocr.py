"""
Stockei - Benchmark de acurácia do OCR de validade.

Roda o MESMO pipeline do produto (/identify/scan-frame: RapidOCR + passada com
realce + validação de formatos) sobre as imagens curadas com gabarito
(manifest.json, status=kept + true_date) e mede:

- acerto exato   (data idêntica ao gabarito)
- acerto mês/ano (dia diferente conta — MM/AA usa fim do mês por regra)
- taxa de leitura (extraiu alguma data plausível)

Gera ml/benchmark_report.md. É o placar oficial: toda mudança no OCR deve
melhorar estes números.

Uso: python ml/benchmark_ocr.py
"""

import json
from datetime import date
from pathlib import Path

SCRAPED = Path(__file__).parent / "dataset" / "scraped"
REPORT = Path(__file__).parent / "benchmark_report.md"


def predict_date(image_bytes: bytes) -> str | None:
    """Pipeline idêntico ao do produto: OCR normal + passada com realce."""
    from backend.vision_identify import enhance_for_ocr, read_package
    from ml.date_validation import extract_date

    def find(texts):
        for t in texts:
            r = extract_date(t["text"])
            if r["date"] and (r["valid"] or r.get("error") == "Produto vencido"):
                return r["date"]
        return None

    found = find(read_package(image_bytes)["texts"])
    if found is None:
        try:
            found = find(read_package(enhance_for_ocr(image_bytes))["texts"])
        except Exception:
            pass
    return found


def run() -> dict:
    manifest = json.loads((SCRAPED / "manifest.json").read_text(encoding="utf-8"))
    cases = [(f, m) for f, m in manifest.items()
             if m.get("status") == "kept" and m.get("true_date")
             and (SCRAPED / f).exists()]
    if not cases:
        print("Nenhuma imagem mantida com gabarito — faça a curadoria primeiro.")
        return {}

    results = []
    for fname, meta in cases:
        pred = predict_date((SCRAPED / fname).read_bytes())
        truth = meta["true_date"]
        exact = pred == truth
        month = bool(pred) and pred[:7] == truth[:7]
        results.append({"file": fname, "query": meta.get("query", ""),
                        "truth": truth, "pred": pred,
                        "exact": exact, "month": month})

    n = len(results)
    read_rate = sum(bool(r["pred"]) for r in results) / n
    exact_acc = sum(r["exact"] for r in results) / n
    month_acc = sum(r["month"] for r in results) / n

    lines = [
        "# Stockei — Benchmark do OCR de Validade",
        f"*Gerado em {date.today().isoformat()} · {n} imagens curadas com gabarito*",
        "",
        "| Métrica | Resultado |",
        "|---|---|",
        f"| Taxa de leitura (extraiu data) | {read_rate:.0%} |",
        f"| Acerto mês/ano | {month_acc:.0%} |",
        f"| Acerto exato | {exact_acc:.0%} |",
        "",
        "## Erros (para guiar o treino do detector de região)",
        "",
        "| Imagem | Gabarito | Lido | Busca de origem |",
        "|---|---|---|---|",
    ]
    for r in results:
        if not r["month"]:
            lines.append(f"| {r['file']} | {r['truth']} | {r['pred'] or '—'} "
                         f"| {r['query'][:40]} |")
    REPORT.write_text("\n".join(lines), encoding="utf-8")

    print(f"{n} imagens · leitura {read_rate:.0%} · mês/ano {month_acc:.0%} "
          f"· exato {exact_acc:.0%}")
    print(f"Relatório: {REPORT}")
    return {"n": n, "read": read_rate, "month": month_acc, "exact": exact_acc}


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))
    run()
