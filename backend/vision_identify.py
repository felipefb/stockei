"""
Stockei - Identificação visual local: lê o texto da embalagem com RapidOCR (ONNX, CPU)
e sugere a descrição do produto. Sem GPU e sem chaves de API.
"""

import io
import logging
import re

logger = logging.getLogger("stockei.vision")

_ocr = None


def _get_ocr():
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR

        _ocr = RapidOCR()
        logger.info("RapidOCR carregado")
    return _ocr


# Textos de embalagem que não descrevem o produto
_NOISE = re.compile(
    r"^(made in|ind[uú]stria|conte[uú]do|peso|lote|val|venc|fab|www\.|sac|cnpj|"
    r"\d{6,}|[\d.,]+\s*(g|kg|ml|l)?)$"
    r"|\b(val|venc|fab|exp|lote)[.:\s]*\d"    # rótulos de data (VAL 12/2027)
    r"|\d{2}[/\-.]\d{2}([/\-.]\d{2,4})?",     # a própria data
    re.IGNORECASE,
)


def read_package(image_bytes: bytes, max_parts: int = 4) -> dict:
    """
    Extrai textos da embalagem e monta uma sugestão de nome.
    Retorna {suggested_name, texts:[{text, confidence, height}]}.
    """
    import numpy as np
    from PIL import Image

    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    result, _ = _get_ocr()(np.array(image))

    texts = []
    for box, text, confidence in result or []:
        clean = text.strip()
        if len(clean) < 3 or confidence < 0.6:
            continue
        height = max(p[1] for p in box) - min(p[1] for p in box)
        texts.append({"text": clean, "confidence": round(float(confidence), 3),
                      "height": round(float(height), 1)})

    # maiores fontes primeiro: marca e nome do produto dominam a embalagem
    ranked = sorted(texts, key=lambda t: t["height"], reverse=True)
    parts, seen = [], set()
    for t in ranked:
        word = t["text"]
        if _NOISE.search(word) or word.lower() in seen:
            continue
        seen.add(word.lower())
        parts.append(word)
        if len(parts) >= max_parts:
            break

    suggested = _prettify(" ".join(parts)) if parts else None
    logger.info("vision: %d textos, sugestao=%r", len(texts), suggested)
    return {"suggested_name": suggested, "texts": texts}


def _prettify(name: str) -> str:
    """CamelCase colado do OCR -> espaçado; capitalização de título."""
    name = re.sub(r"(?<=[a-záéíóúç])(?=[A-ZÁÉÍÓÚÇ])", " ", name)
    name = re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name.title()
