"""
Stockei - Consulta de EAN/GTIN em bases externas para autocompletar a descrição.

Ordem de consulta:
1. Bluesoft Cosmos (melhor cobertura de GTINs brasileiros; requer token gratuito
   em https://cosmos.bluesoft.com.br — variável COSMOS_API_TOKEN)
2. Open Food Facts (gratuita, sem chave; boa para alimentos)

Retorna None quando nenhuma base conhece o código.
"""

import logging
import os

import httpx

logger = logging.getLogger("stockei.lookup")

TIMEOUT = 5.0


def _from_cosmos(ean: str) -> str | None:
    token = os.environ.get("COSMOS_API_TOKEN")
    if not token:
        return None
    try:
        r = httpx.get(
            f"https://api.cosmos.bluesoft.com.br/gtins/{ean}.json",
            headers={"X-Cosmos-Token": token, "User-Agent": "Stockei MVP"},
            timeout=TIMEOUT,
        )
        if r.status_code == 200:
            return r.json().get("description")
    except httpx.HTTPError as exc:
        logger.warning("Cosmos lookup falhou: %s", exc)
    return None


def _from_open_food_facts(ean: str) -> str | None:
    try:
        r = httpx.get(
            f"https://world.openfoodfacts.org/api/v2/product/{ean}.json",
            params={"fields": "product_name,brands,quantity"},
            headers={"User-Agent": "Stockei MVP - contato@stockei.com.br"},
            timeout=TIMEOUT,
        )
        if r.status_code == 200 and r.json().get("status") == 1:
            p = r.json()["product"]
            parts = [p.get("brands"), p.get("product_name"), p.get("quantity")]
            name = " ".join(x for x in parts if x)
            return name or None
    except httpx.HTTPError as exc:
        logger.warning("OpenFoodFacts lookup falhou: %s", exc)
    return None


def lookup_ean(ean: str) -> dict | None:
    """Busca a descrição do produto pelo EAN. Retorna {name, source} ou None."""
    for source, fn in (("cosmos", _from_cosmos), ("openfoodfacts", _from_open_food_facts)):
        name = fn(ean)
        if name:
            logger.info("EAN %s resolvido via %s: %s", ean, source, name)
            return {"name": name, "source": source}
    return None
