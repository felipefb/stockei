"""
Stockei - Identificação de produto por IA multimodal (Claude Haiku 4.5).

Guarda-custos:
- Chamada APENAS sob demanda (botão no portal) — nunca no loop de frames.
- Teto diário configurável: AI_DAILY_LIMIT no .env (default 50 chamadas/dia).
- Contador persistido em ai_usage.json com custo estimado.
- Modelo: claude-haiku-4-5 (US$1/US$5 por MTok) — escolhido pelo usuário
  por custo; ~R$0,01-0,02 por identificação.
"""

import base64
import json
import logging
import os
from datetime import date
from pathlib import Path

try:  # garante ANTHROPIC_API_KEY do .env mesmo fora do app principal
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger("stockei.ai")

MODEL = os.environ.get("AI_MODEL", "claude-haiku-4-5")
DAILY_LIMIT = int(os.environ.get("AI_DAILY_LIMIT", "50"))
USAGE_FILE = Path(os.environ.get("AI_USAGE_FILE", "ai_usage.json"))

# preço Haiku 4.5 (USD por 1M tokens) para estimativa exibida ao usuário
_PRICE_IN, _PRICE_OUT = 1.00, 5.00
_USD_BRL = 5.5

_SCHEMA = {
    "type": "object",
    "properties": {
        "brand": {"type": ["string", "null"]},
        "product_name": {"type": "string"},
        "variant": {"type": ["string", "null"]},
        "size": {"type": ["string", "null"]},
        "category": {"type": ["string", "null"]},
        "confidence": {"type": "string", "enum": ["alta", "media", "baixa"]},
    },
    "required": ["brand", "product_name", "variant", "size", "category", "confidence"],
    "additionalProperties": False,
}

_PROMPT = (
    "Você identifica produtos de varejo brasileiro pela embalagem. "
    "Analise a foto e extraia marca, nome do produto, variante/sabor, "
    "tamanho (ex.: 90g, 2L) e categoria (Laticínios, Bebidas, Mercearia, "
    "Higiene, Limpeza, Medicamentos, Acessórios ou outra). "
    "Se algo não estiver legível, use null. confidence reflete a legibilidade geral."
)


def _load_usage() -> dict:
    try:
        data = json.loads(USAGE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        data = {}
    today = date.today().isoformat()
    if data.get("date") != today:
        data = {"date": today, "calls": 0, "input_tokens": 0, "output_tokens": 0}
    return data


def _save_usage(data: dict) -> None:
    USAGE_FILE.write_text(json.dumps(data), encoding="utf-8")


def usage_stats() -> dict:
    data = _load_usage()
    cost_usd = (data["input_tokens"] * _PRICE_IN + data["output_tokens"] * _PRICE_OUT) / 1_000_000
    return {
        "enabled": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "model": MODEL,
        "today_calls": data["calls"],
        "daily_limit": DAILY_LIMIT,
        "remaining": max(0, DAILY_LIMIT - data["calls"]),
        "est_cost_today_brl": round(cost_usd * _USD_BRL, 4),
    }


class AILimitReached(Exception):
    pass


def _call_vision(image_bytes: bytes, media_type: str, system: str,
                 schema: dict, question: str) -> dict:
    """Chamada multimodal com structured output, respeitando o teto diário."""
    usage = _load_usage()
    if usage["calls"] >= DAILY_LIMIT:
        raise AILimitReached(f"Teto diário de {DAILY_LIMIT} identificações por IA atingido")

    import anthropic

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=system,
        output_config={"format": {"type": "json_schema", "schema": schema}},
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": base64.standard_b64encode(image_bytes).decode(),
                    },
                },
                {"type": "text", "text": question},
            ],
        }],
    )

    usage["calls"] += 1
    usage["input_tokens"] += response.usage.input_tokens
    usage["output_tokens"] += response.usage.output_tokens
    _save_usage(usage)

    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)


def identify_package(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """Identifica o produto na foto. Levanta AILimitReached se o teto diário acabou."""
    result = _call_vision(image_bytes, media_type, _PROMPT, _SCHEMA,
                          "Identifique este produto.")

    parts = [result.get("brand"), result.get("product_name"),
             result.get("variant"), result.get("size")]
    result["suggested_name"] = " ".join(p for p in parts if p)
    logger.info("IA identificou: %r (confiança %s)",
                result["suggested_name"], result["confidence"])
    return result


_EXPIRY_SCHEMA = {
    "type": "object",
    "properties": {
        "expiry_date": {"type": ["string", "null"]},  # ISO YYYY-MM-DD ou null
        "raw_text": {"type": ["string", "null"]},     # como está impresso
        "confidence": {"type": "string", "enum": ["alta", "media", "baixa"]},
    },
    "required": ["expiry_date", "raw_text", "confidence"],
    "additionalProperties": False,
}

_EXPIRY_PROMPT = (
    "Você lê datas de VALIDADE em embalagens brasileiras: jato de tinta, "
    "relevo em metal (latas), carimbo. Formatos comuns: DD/MM/AAAA, DD/MM/AA, "
    "MM/AA, 'DD MM AA' com espaços. Rótulos V/VAL/VENC/EXP indicam validade; "
    "F/FAB é fabricação e deve ser IGNORADA. Sem rótulos, a validade é a data "
    "mais distante no futuro. Para MM/AA use o último dia do mês. "
    "Responda expiry_date em ISO (YYYY-MM-DD) ou null se ilegível."
)


def read_expiry(image_bytes: bytes, media_type: str = "image/jpeg") -> dict:
    """Lê a data de validade na foto (fallback quando o OCR local falha)."""
    result = _call_vision(image_bytes, media_type, _EXPIRY_PROMPT, _EXPIRY_SCHEMA,
                          "Qual é a data de validade deste produto?")
    logger.info("IA leu validade: %s (%r, confiança %s)",
                result["expiry_date"], result["raw_text"], result["confidence"])
    return result
