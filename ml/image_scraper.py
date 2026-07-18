"""
Stockei - Coletor de imagens para o dataset de validades/códigos de barras.

Busca imagens na web (DuckDuckGo Images), baixa, filtra por tamanho,
remove duplicatas por hash e gera um manifest para a tela de curadoria
(portal/curadoria.html), onde o humano faz o double-check: aprova/descarta
e anota a data verdadeira (gabarito).

Uso:
  python ml/image_scraper.py                     # queries padrão de validade
  python ml/image_scraper.py --per-query 40
  python ml/image_scraper.py --queries "codigo de barras curvo lata"
"""

import argparse
import hashlib
import json
import time
from pathlib import Path

OUT_DIR = Path(__file__).parent / "dataset" / "scraped"
MANIFEST = OUT_DIR / "manifest.json"
MIN_SIDE = 250          # descarta thumbnails minúsculos
TIMEOUT = 12

DEFAULT_QUERIES = [
    "data de validade estampada lata",
    "data validade jato de tinta embalagem",
    "validade impressa tampa pote",
    "lote validade gravado metal lata",
    "data de validade embalagem produto brasil",
    "expiration date stamped can lid",
    "expiry date inkjet printed package",
]


def _download(url: str, dest: Path) -> bool:
    import httpx

    try:
        r = httpx.get(url, timeout=TIMEOUT, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200 or len(r.content) < 8_000:
            return False
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(r.content))
        img.verify()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        if min(img.size) < MIN_SIDE:
            return False
        img.save(dest, "JPEG", quality=90)
        return True
    except Exception:
        return False


def scrape(queries: list[str], per_query: int = 30) -> dict:
    from ddgs import DDGS

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    seen_hashes = {m["sha1"] for m in manifest.values() if "sha1" in m}
    stats = {"found": 0, "downloaded": 0, "duplicates": 0, "rejected": 0}

    with DDGS() as ddgs:
        for query in queries:
            print(f"→ buscando: {query!r}")
            try:
                results = list(ddgs.images(query, max_results=per_query))
            except Exception as exc:
                print(f"  busca falhou: {exc}")
                continue
            stats["found"] += len(results)
            for item in results:
                url = item.get("image")
                if not url:
                    continue
                name = hashlib.sha1(url.encode()).hexdigest()[:16] + ".jpg"
                dest = OUT_DIR / name
                if name in manifest:
                    stats["duplicates"] += 1
                    continue
                if not _download(url, dest):
                    stats["rejected"] += 1
                    continue
                sha1 = hashlib.sha1(dest.read_bytes()).hexdigest()
                if sha1 in seen_hashes:  # mesma imagem em URL diferente
                    dest.unlink()
                    stats["duplicates"] += 1
                    continue
                seen_hashes.add(sha1)
                manifest[name] = {"url": url, "query": query, "sha1": sha1,
                                  "status": "pending"}  # pending|kept|discarded
                stats["downloaded"] += 1
            time.sleep(1.0)  # educado com o serviço

    MANIFEST.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"\nColeta: {stats['downloaded']} novas de {stats['found']} encontradas "
          f"({stats['duplicates']} duplicadas, {stats['rejected']} rejeitadas).")
    print(f"Curadoria: abra /portal/curadoria.html para aprovar e anotar as datas.")
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", nargs="*", default=DEFAULT_QUERIES)
    parser.add_argument("--per-query", type=int, default=30)
    args = parser.parse_args()
    scrape(args.queries, args.per_query)
